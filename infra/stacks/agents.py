"""NimbusAgents: Vishwa's stack (agents/). One Lambda per agent, woken by EventBridge rules.

Names come from NimbusShared's SSM parameters under /nimbus/, resolved at deploy
time, never hard-coded. Every agent Lambda shares one code bundle: agents/ plus
the contracts package, the risk engine (engines/risk, bundled as `risk`) and the
fixtures (the Sentinel's fallback outside a Michaung Replay).

Context values (cdk.json or `-c key=value`):
  nova_lite_id, nova_pro_id   Bedrock inference-profile IDs from issue #1
  send_push_function          the send-push Lambda name (default nimbus-send-push, as
                              NimbusApi names it in #6); "" leaves the Herald without it

Bundling runs in the Lambda Python 3.12 build image. With Podman instead of
Docker, set CDK_DOCKER=podman. Tests skip bundling (aws:cdk:bundling-stacks).
"""

from dataclasses import dataclass
from pathlib import Path

from aws_cdk import ArnFormat, BundlingOptions, Duration, RemovalPolicy, Stack
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_ssm as ssm
from constructs import Construct

REPO_ROOT = Path(__file__).resolve().parents[2]
SSM_PREFIX = "/nimbus"

# Pinned to the versions agents/uv.lock was tested with.
RUNTIME_PACKAGES = ("cedarpy==4.12.1", "strands-agents==1.59.0", "boto3==1.43.111", "pydantic==2.14.0")
AGENT_PACKAGES = ("common", "policies", "sentinel", "herald")

DEFAULT_NOVA_LITE_ID = "us.amazon.nova-lite-v1:0"
DEFAULT_NOVA_PRO_ID = "us.amazon.nova-pro-v1:0"
DEFAULT_SEND_PUSH_FUNCTION = "nimbus-send-push"  # NimbusApi (#6) names it so
# A "us." inference profile routes to these regions, and each needs its own model permission.
NOVA_PROFILE_REGIONS = ("us-east-1", "us-east-2", "us-west-2")


@dataclass(frozen=True)
class AgentSpec:
    name: str
    handler: str
    wakes_on: tuple[str, ...]
    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()
    uses_nova_lite: bool = False
    sends_push: bool = False
    timeout_s: int = 30


AGENTS: tuple[AgentSpec, ...] = (
    AgentSpec(
        "sentinel",
        "sentinel.handler.handler",
        wakes_on=("clock.tick",),
        reads=("Segments",),
        writes=("SegmentRisk",),  # its single writer (#32)
        uses_nova_lite=True,  # rewrites the top reason
        timeout_s=120,  # first tick rewrites up to one reason per band change
    ),
    AgentSpec(
        "herald",
        "herald.handler.handler",
        wakes_on=("risk.changed", "proposal.decided"),
        reads=("PlaceIndex", "SegmentRisk"),
        sends_push=True,
    ),
)

# Written only by the projector in api/ (#32). No agent may write these.
PROJECTOR_TABLES = ("Activity", "Proposals", "Alerts", "Hazards", "Readings", "Sos")

TABLE_READ = ["dynamodb:GetItem", "dynamodb:BatchGetItem", "dynamodb:Query", "dynamodb:Scan"]
TABLE_WRITE = ["dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:BatchWriteItem"]


def nova_foundation_model(profile_id: str) -> str:
    """us.amazon.nova-lite-v1:0 -> amazon.nova-lite-v1:0"""
    return profile_id.split(".", 1)[1] if profile_id.startswith(("us.", "eu.", "apac.")) else profile_id


class NimbusAgents(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.nova_lite_id = self.node.try_get_context("nova_lite_id") or DEFAULT_NOVA_LITE_ID
        self.nova_pro_id = self.node.try_get_context("nova_pro_id") or DEFAULT_NOVA_PRO_ID
        send_push = self.node.try_get_context("send_push_function")
        self.send_push_function = DEFAULT_SEND_PUSH_FUNCTION if send_push is None else send_push

        bus_name = self._ssm("bus/name")
        self.bus = events.EventBus.from_event_bus_name(self, "Bus", bus_name)
        self.code = self._bundle()

        self.functions: dict[str, lambda_.Function] = {}
        for spec in AGENTS:
            self.functions[spec.name] = self._agent(spec, bus_name)

    # --- pieces -----------------------------------------------------------------

    def _ssm(self, path: str) -> str:
        return ssm.StringParameter.value_for_string_parameter(self, f"{SSM_PREFIX}/{path}")

    def _table_arn(self, table: str) -> str:
        return self.format_arn(service="dynamodb", resource="table", resource_name=self._ssm(f"tables/{table}"))

    def _bundle(self) -> lambda_.Code:
        install = " ".join(["/asset-input/contracts", *RUNTIME_PACKAGES])
        copy = " ".join(f"/asset-input/agents/{p}" for p in AGENT_PACKAGES)
        command = (
            f"pip install --no-cache-dir --quiet --target /asset-output {install}"
            f" && cp -r {copy} /asset-output/"
            " && cp -r /asset-input/engines/risk /asset-output/risk"
            " && mkdir -p /asset-output/contracts && cp -r /asset-input/contracts/fixtures /asset-output/contracts/"
            " && find /asset-output -name __pycache__ -prune -exec rm -rf {} +"
        )
        return lambda_.Code.from_asset(
            str(REPO_ROOT),
            exclude=[
                "*",
                "!agents",
                *(f"!agents/{p}" for p in AGENT_PACKAGES),
                *(f"!agents/{p}/**" for p in AGENT_PACKAGES),
                "!engines",
                "!engines/risk",
                "!engines/risk/**",
                "!contracts",
                "!contracts/pyproject.toml",
                "!contracts/README.md",
                "!contracts/src",
                "!contracts/src/**",
                "!contracts/fixtures",
                "!contracts/fixtures/**",
                "**/__pycache__",
                "**/.venv",
            ],
            bundling=BundlingOptions(
                image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                command=["bash", "-c", command],
                # Rootless Podman maps the host user to root; SELinux (Fedora) needs label=disable for the mounts.
                user="root",
                security_opt="label=disable",
                environment={"PIP_CACHE_DIR": "/tmp/pip", "HOME": "/tmp"},
            ),
        )

    def _agent(self, spec: AgentSpec, bus_name: str) -> lambda_.Function:
        name = spec.name.title()
        environment = {
            "NIMBUS_EVENT_BUS": bus_name,
            "NIMBUS_NOVA_LITE_ID": self.nova_lite_id,
            "NIMBUS_NOVA_PRO_ID": self.nova_pro_id,
        }
        if spec.sends_push and self.send_push_function:
            environment["NIMBUS_SEND_PUSH_FUNCTION"] = self.send_push_function
        # agents/common/dynamo.py reads NIMBUS_TABLE_<NAME>; without it an agent falls back to memory.
        for table in dict.fromkeys((*spec.reads, *spec.writes)):
            environment[f"NIMBUS_TABLE_{table.upper()}"] = self._ssm(f"tables/{table}")

        fn = lambda_.Function(
            self,
            f"{name}Function",
            function_name=f"nimbus-agent-{spec.name}",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.X86_64,
            handler=spec.handler,
            code=self.code,
            memory_size=512,
            timeout=Duration.seconds(spec.timeout_s),
            environment=environment,
            log_group=logs.LogGroup(
                self,
                f"{name}Logs",
                log_group_name=f"/aws/lambda/nimbus-agent-{spec.name}",
                retention=logs.RetentionDays.ONE_WEEK,
                removal_policy=RemovalPolicy.DESTROY,
            ),
        )

        fn.add_to_role_policy(iam.PolicyStatement(actions=["events:PutEvents"], resources=[self._ssm("bus/arn")]))
        if spec.reads:
            fn.add_to_role_policy(iam.PolicyStatement(actions=TABLE_READ, resources=[self._table_arn(t) for t in spec.reads]))
        if spec.writes:
            fn.add_to_role_policy(iam.PolicyStatement(actions=TABLE_WRITE, resources=[self._table_arn(t) for t in spec.writes]))
        if spec.uses_nova_lite:
            fn.add_to_role_policy(self._bedrock_statement(self.nova_lite_id))
        if spec.sends_push and self.send_push_function:
            fn.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["lambda:InvokeFunction"],
                    resources=[self.format_arn(service="lambda", resource="function", resource_name=self.send_push_function, arn_format=ArnFormat.COLON_RESOURCE_NAME)],
                )
            )

        for event_type in spec.wakes_on:
            rule = events.Rule(
                self,
                f"{name}On{''.join(p.title() for p in event_type.split('.'))}",
                event_bus=self.bus,
                description=f"Wake the {spec.name} on {event_type}",
                event_pattern=events.EventPattern(detail_type=[event_type], source=events.Match.prefix("nimbus.")),
            )
            # Replays run on a fast clock: a stale tick isn't worth retrying for a day.
            rule.add_target(targets.LambdaFunction(fn, retry_attempts=2, max_event_age=Duration.hours(1)))
        return fn

    def _bedrock_statement(self, profile_id: str) -> iam.PolicyStatement:
        model = nova_foundation_model(profile_id)
        resources = [f"arn:aws:bedrock:{region}::foundation-model/{model}" for region in NOVA_PROFILE_REGIONS]
        if profile_id != model:
            resources.append(self.format_arn(service="bedrock", resource="inference-profile", resource_name=profile_id))
        return iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=resources)

