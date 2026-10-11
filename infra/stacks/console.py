"""NimbusConsole: Amplify hosting for Derrick's console build. Filled in by issue #29."""

from aws_cdk import Stack
from constructs import Construct


class NimbusConsole(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
