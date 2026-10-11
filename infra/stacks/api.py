"""NimbusApi: the event projector now; HTTP API routes and the FCM sender come with issues #8, #7, #6.

The projector (api/projector/) copies bus events into the tables the console and app read.
It may write only the tables below. Every other table has its own writer (api/README.md).
"""

from pathlib import Path

from aws_cdk import BundlingOptions, Duration, Stack
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_sqs as sqs
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

# Everything the projector bundle doesn't need, so the asset hash only moves when api/ or contracts/ do.
_EXCLUDE = [
    ".git", ".github", "agents", "app", "console", "docs", "engines", "infra", "replay",
    "NIMBUS-Design-Lock.pdf", "**/.venv", "**/__pycache__", "**/.pytest_cache", "**/cdk.out", "**/node_modules",
]


def _projector_code() -> lambda_.Code:
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
                "pip install --no-cache-dir ./contracts -t /asset-output && cp -r api/projector /asset-output/projector",
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

        self.projector_dlq = sqs.Queue(self, "ProjectorDlq", retention_period=Duration.days(14))

        self.projector = lambda_.Function(
            self,
            "Projector",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="projector.handler.handler",
            code=_projector_code(),
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
