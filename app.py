#!/usr/bin/env python3

from aws_cdk import core

from asetuapi.asetuapi_stack import AsetuapiStack
from asetuapi.asetuapi_frontend import AsetuapiFrontendStack

from generate_exports_and_bundle import generate_exports_and_bundle
from create_dependency_layer import create_dependency_layer

# region should be ap-south-1 as Aarogya Setu OpenAPI might not work
# from different geos
deploy_env = core.Environment(region="ap-south-1")

app = core.App()
backend = AsetuapiStack(app, "asetuapi", create_dependency_layer, env=deploy_env)
AsetuapiFrontendStack(
    app, "asetuapifrontend", generate_exports_and_bundle, env=deploy_env
)

app.synth()
