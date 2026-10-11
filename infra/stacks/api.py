"""NimbusApi: the event projector, the console HTTP API and the citizen HTTP API. The FCM sender comes with #6.

The projector (api/projector/) copies bus events into the tables the console and app read.
It may write only the tables below. Every other table has its own writer (api/README.md).

The console API (api/console/) reads those tables and updates one thing: a Proposal's decision.
The citizen API (api/citizen/) serves the Flutter app: devices, Saved Places (and the PlaceIndex that
follows them), Segments, risk and Readings. All three Lambdas share one bundle.
"""

from pathlib import Path

from aws_cdk import BundlingOptions, CfnOutput, Duration, Stack
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_sqs as sqs
from aws_cdk import aws_ssm as ssm
from constructs import Construct

from stacks.shared import NimbusShared

REPO = Path(__file__).resolve().parents[2]

# Keep in step with PROJECTED and KEYS in api/projector/core.py. api/tests/test_projector.py checks it.
PROJECTED_EVENT_TYPES = (
    "agent.activity",
    "policy.decided",
    "proposal.created",
    "alert.sent",
    "hazard.detected",
    "report.verified",
    "sos.created",
    "sos.ranked",
)
WRITTEN_TABLES = ("Activity", "Proposals", "Alerts", "Hazards", "Readings", "Sos")

# Keep in step with Console.router.table and TABLE_KEYS in api/console. api/tests/test_console.py checks it.
CONSOLE_ROUTES = (
    ("GET", "/risk"),
    ("GET", "/readings"),
    ("GET", "/hazards"),
    ("GET", "/resources"),
    ("GET", "/sos"),
    ("GET", "/proposals"),
    ("GET", "/activity"),
    ("POST", "/proposals/{proposal_id}/decision"),
)
# Read-only, except a Proposal's decision (UpdateItem on Proposals).
CONSOLE_READ_TABLES = ("SegmentRisk", "Readings", "Hazards", "Resources", "Sos", "Proposals", "Activity", "Runs")
CONSOLE_UPDATED_TABLE = "Proposals"

# Both HTTP APIs are open until issue #19 adds auth, so each gets a ceiling: a runaway client or a
# stranger who finds the URL can't run up Lambda and DynamoDB charges. Per route, requests per second.
# A console polling /activity every 2 s uses 0.5 rps, so this leaves plenty of headroom.
THROTTLE_RATE_LIMIT = 25
THROTTLE_BURST_LIMIT = 50

# Keep in step with Citizen.router.table and TABLE_KEYS in api/citizen. api/tests/test_citizen.py checks it.
CITIZEN_ROUTES = (
    ("GET", "/segments"),
    ("GET", "/risk"),
    ("GET", "/readings"),
    ("POST", "/devices"),
    ("GET", "/saved-places"),
    ("PUT", "/saved-places/{place_id}"),
    ("DELETE", "/saved-places/{place_id}"),
)
CITIZEN_READ_TABLES = ("Segments", "SegmentRisk", "Readings")
# Put and delete only, except SavedPlaces which is also read back. Devices is never read by the API.
CITIZEN_WRITE_TABLES = ("Devices", "SavedPlaces", "PlaceIndex")

# Everything the bundle doesn't need, so the asset hash only moves when api/ or contracts/ do.
_EXCLUDE = [
    ".git", ".github", "agents", "app", "console", "docs", "engines", "infra", "replay",
    "NIMBUS-Design-Lock.pdf", "**/.venv", "**/__pycache__", "**/.pytest_cache", "**/cdk.out", "**/node_modules",
]


def _api_code() -> lambda_.Code:
    # Needs a container runtime (Docker, or Podman with CDK_DOCKER=podman) at synth. Tests
    # skip it with the context {"aws:cdk:bundling-stacks": []}.
    return lambda_.Code.from_asset(
        str(REPO),
        exclude=_EXCLUDE,
        bundling=BundlingOptions(
            image=lambda_.Runtime.PYTHON_3_12.bundling_image,
            command=[
                "bash",
                "-c",
                "pip install --no-cache-dir ./contracts -t /asset-output && cp -r api/projector api/console api/citizen /asset-output/",
            ],
            # Same options as stacks/agents.py. Rootless Podman maps the host user to root, and
            # SELinux (Fedora) needs label=disable for the mounts. Harmless under Docker.
            user="root",
            security_opt="label=disable",
            environment={"PIP_CACHE_DIR": "/tmp/pip", "HOME": "/tmp"},
        ),
    )


class NimbusApi(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, shared: NimbusShared, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        code = _api_code()
        self._projector(shared, code)
        self._console(shared, code)
        self._citizen(shared, code)

    def _projector(self, shared: NimbusShared, code: lambda_.Code) -> None:
        self.projector_dlq = sqs.Queue(self, "ProjectorDlq", retention_period=Duration.days(14))

        self.projector = lambda_.Function(
            self,
            "Projector",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="projector.handler.handler",
            code=code,
            memory_size=256,
            timeout=Duration.seconds(30),
            description="Copies nimbus.* events into the console and app tables",
            environment={f"NIMBUS_TABLE_{name.upper()}": shared.tables[name].table_name for name in WRITTEN_TABLES},
        )
        for name in WRITTEN_TABLES:
            shared.tables[name].grant_write_data(self.projector)

        events.Rule(
            self,
            "ProjectorRule",
            event_bus=shared.bus,
            description="Projected nimbus.* events to the projector Lambda",
            event_pattern=events.EventPattern(
                source=events.Match.prefix("nimbus."),
                detail_type=list(PROJECTED_EVENT_TYPES),
            ),
            targets=[targets.LambdaFunction(self.projector, dead_letter_queue=self.projector_dlq, retry_attempts=2)],
        )

    def _console(self, shared: NimbusShared, code: lambda_.Code) -> None:
        self.console = lambda_.Function(
            self,
            "Console",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="console.handler.handler",
            code=code,
            memory_size=256,
            timeout=Duration.seconds(15),
            description="Ward console HTTP API: reads, and officers' decisions on Proposals",
            environment={
                "NIMBUS_EVENT_BUS": shared.bus.event_bus_name,
                **{f"NIMBUS_TABLE_{name.upper()}": shared.tables[name].table_name for name in CONSOLE_READ_TABLES},
            },
        )
        for name in CONSOLE_READ_TABLES:
            shared.tables[name].grant_read_data(self.console)
        shared.tables[CONSOLE_UPDATED_TABLE].grant(self.console, "dynamodb:UpdateItem")
        shared.bus.grant_put_events_to(self.console)  # to emit proposal.decided

        self.console_api = apigw.HttpApi(
            self,
            "ConsoleApi",
            api_name="nimbus-console",
            create_default_stage=False,
            description="NIMBUS ward console API (issue #8). No authorizer until issue #19.",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=["*"],  # tighten to the Amplify domain with #29
                allow_methods=[apigw.CorsHttpMethod.GET, apigw.CorsHttpMethod.POST, apigw.CorsHttpMethod.OPTIONS],
                allow_headers=["content-type"],
                max_age=Duration.hours(1),
            ),
        )
        apigw.HttpStage(
            self,
            "ConsoleStage",
            http_api=self.console_api,
            auto_deploy=True,
            throttle=apigw.ThrottleSettings(rate_limit=THROTTLE_RATE_LIMIT, burst_limit=THROTTLE_BURST_LIMIT),
        )
        integration = integrations.HttpLambdaIntegration("ConsoleIntegration", self.console)
        for method, path in CONSOLE_ROUTES:
            self.console_api.add_routes(path=path, methods=[apigw.HttpMethod(method)], integration=integration)

        ssm.StringParameter(
            self, "ParamApiConsoleUrl", parameter_name="/nimbus/api/console-url", string_value=self.console_api.api_endpoint
        )
        CfnOutput(self, "ConsoleApiUrl", value=self.console_api.api_endpoint)

    def _citizen(self, shared: NimbusShared, code: lambda_.Code) -> None:
        self.citizen = lambda_.Function(
            self,
            "Citizen",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="citizen.handler.handler",
            code=code,
            memory_size=256,
            timeout=Duration.seconds(15),
            description="Citizen app HTTP API: devices, Saved Places, Segments, risk, Readings",
            environment={
                f"NIMBUS_TABLE_{name.upper()}": shared.tables[name].table_name
                for name in (*CITIZEN_READ_TABLES, *CITIZEN_WRITE_TABLES)
            },
        )
        for name in CITIZEN_READ_TABLES:
            shared.tables[name].grant_read_data(self.citizen)
        shared.tables["SavedPlaces"].grant_read_data(self.citizen)
        for name in CITIZEN_WRITE_TABLES:
            actions = ["dynamodb:PutItem"] if name == "Devices" else ["dynamodb:PutItem", "dynamodb:DeleteItem"]
            shared.tables[name].grant(self.citizen, *actions)

        self.citizen_api = apigw.HttpApi(
            self,
            "CitizenApi",
            api_name="nimbus-citizen",
            create_default_stage=False,
            description="NIMBUS citizen app API (issue #7). Identified by X-Install-Id until issue #19.",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[
                    apigw.CorsHttpMethod.GET,
                    apigw.CorsHttpMethod.POST,
                    apigw.CorsHttpMethod.PUT,
                    apigw.CorsHttpMethod.DELETE,
                    apigw.CorsHttpMethod.OPTIONS,
                ],
                allow_headers=["content-type", "x-install-id"],
                max_age=Duration.hours(1),
            ),
        )
        apigw.HttpStage(
            self,
            "CitizenStage",
            http_api=self.citizen_api,
            auto_deploy=True,
            throttle=apigw.ThrottleSettings(rate_limit=THROTTLE_RATE_LIMIT, burst_limit=THROTTLE_BURST_LIMIT),
        )
        integration = integrations.HttpLambdaIntegration("CitizenIntegration", self.citizen)
        for method, path in CITIZEN_ROUTES:
            self.citizen_api.add_routes(path=path, methods=[apigw.HttpMethod(method)], integration=integration)

        ssm.StringParameter(
            self, "ParamApiCitizenUrl", parameter_name="/nimbus/api/citizen-url", string_value=self.citizen_api.api_endpoint
        )
        CfnOutput(self, "CitizenApiUrl", value=self.citizen_api.api_endpoint)
