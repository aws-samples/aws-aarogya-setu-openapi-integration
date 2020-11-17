#!/usr/bin/env python3

from aws_cdk import core

from asetuapi.asetuapi_stack import AsetuapiStack
from asetuapi.asetuapi_frontend import AsetuapiFrontendStack


app = core.App()
backend = AsetuapiStack(app, "asetuapi")
AsetuapiFrontendStack(app, "asetuapifrontend")

app.synth()
