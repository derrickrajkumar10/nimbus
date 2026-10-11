"""NimbusEngines: Goutam's stack (engines/, replay/). Empty until he fills it in.

Look up the bus, tables and buckets from the SSM parameters under /nimbus/
(see stacks/shared.py) instead of importing them from NimbusShared.
"""

from aws_cdk import Stack
from constructs import Construct


class NimbusEngines(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
