"""NimbusApi: HTTP API and Lambdas (api/). Filled in by issues #7, #8 and #19."""

from aws_cdk import Stack
from constructs import Construct


class NimbusApi(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
