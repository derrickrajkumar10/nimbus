"""NIMBUS CDK app. One stack per lane, all in us-east-1 (ADR 0004).

Deploy a single stack by name, for example `cdk deploy NimbusShared`, so lanes
don't collide. See README.md.
"""

import os

import aws_cdk as cdk

from stacks.agents import NimbusAgents
from stacks.api import NimbusApi
from stacks.console import NimbusConsole
from stacks.engines import NimbusEngines
from stacks.shared import NimbusShared

REGION = "us-east-1"

app = cdk.App()
env = cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region=REGION)

NimbusShared(app, "NimbusShared", env=env)
NimbusEngines(app, "NimbusEngines", env=env)  # Goutam
NimbusAgents(app, "NimbusAgents", env=env)  # Vishwa
NimbusApi(app, "NimbusApi", env=env)  # Varun
NimbusConsole(app, "NimbusConsole", env=env)  # Varun, hosting Derrick's build

app.synth()
