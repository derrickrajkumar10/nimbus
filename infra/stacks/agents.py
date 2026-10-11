"""NimbusAgents: Vishwa's stack (agents/). Empty until he fills it in.

Look up the bus, tables and buckets from the SSM parameters under /nimbus/
(see stacks/shared.py). Agent Lambdas get NIMBUS_EVENT_BUS from /nimbus/bus/name.
"""

from aws_cdk import Stack
from constructs import Construct


class NimbusAgents(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
