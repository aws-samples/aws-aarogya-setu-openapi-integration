#!/usr/bin/env python3

from aws_cdk import core

from asetuapi.asetuapi_stack import AsetuapiStack
from asetuapi.asetuapi_frontend import AsetuapiFrontendStack
from asetuapi.pipeline import DeployPipelineStack


app = core.App()
backend = AsetuapiStack(app, "asetuapi")
AsetuapiFrontendStack(app, "asetuapifrontend", table=backend.display_table)
DeployPipelineStack(
    app,
    "asetuapidevops",
)

app.synth()
