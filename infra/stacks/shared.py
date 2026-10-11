"""NimbusShared: the bus, tables and buckets every lane writes to.

Lanes find these by SSM parameter and never hard-code names:

    /nimbus/bus/name, /nimbus/bus/arn
    /nimbus/tables/<Table>          the table name, one per row of contracts/storage.md
    /nimbus/buckets/photos          Report and SOS photos: reports/{run_id}/{report_id}.jpg
    /nimbus/buckets/data            F1 output: segments/v{n}/segments.geojson
"""

from dataclasses import dataclass

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_events as events
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_ssm as ssm
from constructs import Construct

BUS_NAME = "nimbus"
ARCHIVE_RETENTION_DAYS = 7
SSM_PREFIX = "/nimbus"


@dataclass(frozen=True)
class TableSpec:
    name: str
    pk: str
    sk: str | None = None
    retain: bool = False  # keep the data if the stack is deleted


# Mirrors contracts/storage.md. tests/test_shared.py fails if the two drift apart.
# A key written `run_id#segment_id` there is one attribute with that literal name, holding
# values such as "live#27320162-0". Every key attribute is a string.
TABLES: tuple[TableSpec, ...] = (
    TableSpec("Segments", "segment_id", retain=True),  # F1 output is slow to rebuild
    TableSpec("SegmentRisk", "run_id", "segment_id"),
    TableSpec("Reports", "run_id", "report_id"),
    TableSpec("Readings", "run_id", "reading_id"),
    TableSpec("Hazards", "run_id", "hazard_id"),
    TableSpec("Sos", "run_id", "sos_id"),
    TableSpec("Resources", "run_id", "resource_id"),
    TableSpec("Proposals", "run_id", "proposal_id"),
    TableSpec("Alerts", "run_id", "alert_id"),
    TableSpec("Activity", "run_id", "emitted_at#event_id"),
    TableSpec("Ledger", "run_id#segment_id", "sim_time"),
    TableSpec("Reporters", "run_id", "reporter_id"),
    TableSpec("Runs", "run_id"),
    TableSpec("Devices", "device_id"),
    TableSpec("SavedPlaces", "device_id", "place_id"),
    TableSpec("PlaceIndex", "run_id#segment_id", "device_id#place_id"),
)


def table_name(spec_name: str) -> str:
    return f"nimbus-{spec_name}"


class NimbusShared(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.bus = events.EventBus(self, "Bus", event_bus_name=BUS_NAME)
        # Replay events for debugging. Only events the agents publish: source "nimbus.<name>".
        self.bus.archive(
            "Archive",
            archive_name="nimbus-events",
            description="Every nimbus.* event, for debugging",
            event_pattern=events.EventPattern(source=events.Match.prefix("nimbus.")),
            retention=Duration.days(ARCHIVE_RETENTION_DAYS),
        )
        self._param("bus/name", self.bus.event_bus_name)
        self._param("bus/arn", self.bus.event_bus_arn)

        self.tables: dict[str, dynamodb.Table] = {}
        for spec in TABLES:
            self.tables[spec.name] = self._table(spec)
            self._param(f"tables/{spec.name}", self.tables[spec.name].table_name)

        self.photos = self._bucket("Photos", retain=False, cors=True)
        self.data = self._bucket("Data", retain=True, cors=False)
        self._param("buckets/photos", self.photos.bucket_name)
        self._param("buckets/data", self.data.bucket_name)

    def _table(self, spec: TableSpec) -> dynamodb.Table:
        return dynamodb.Table(
            self,
            f"{spec.name}Table",
            table_name=table_name(spec.name),
            partition_key=dynamodb.Attribute(name=spec.pk, type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name=spec.sk, type=dynamodb.AttributeType.STRING) if spec.sk else None,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN if spec.retain else RemovalPolicy.DESTROY,
        )

    def _bucket(self, name: str, *, retain: bool, cors: bool) -> s3.Bucket:
        return s3.Bucket(
            self,
            f"{name}Bucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.RETAIN if retain else RemovalPolicy.DESTROY,
            auto_delete_objects=not retain,
            # The app uploads photos with presigned PUT URLs and the console shows them with presigned GETs.
            cors=[s3.CorsRule(allowed_methods=[s3.HttpMethods.PUT, s3.HttpMethods.GET], allowed_origins=["*"], allowed_headers=["*"])]
            if cors
            else None,
        )

    def _param(self, path: str, value: str) -> None:
        ssm.StringParameter(
            self,
            "Param" + "".join(part.title() for part in path.replace("/", " ").split()),
            parameter_name=f"{SSM_PREFIX}/{path}",
            string_value=value,
        )
