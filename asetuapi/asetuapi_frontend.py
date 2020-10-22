from aws_cdk import (
    core,
    aws_s3 as s3,
    aws_s3_deployment as s3_dep,
    aws_cloudfront as cloudfront,
    aws_dynamodb as ddb,
)

from cdk_dynamo_table_viewer import TableViewer


class AsetuapiFrontendStack(core.Stack):
    def __init__(
        self, scope: core.Construct, id: str, table: ddb.Table, **kwargs
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # deploy application to s3 bucket behind cloudfront
        bucket = s3.Bucket(
            self,
            "ReactAppBucket",
            website_index_document="index.html",
        )

        src = s3_dep.BucketDeployment(
            self,
            "DeployReactApp",
            sources=[s3_dep.Source.asset("client/build")],
            destination_bucket=bucket,
        )

        oai = cloudfront.OriginAccessIdentity(self, "OAI")
        cfd = cloudfront.CloudFrontWebDistribution(
            self,
            "ReactAppDistribution",
            origin_configs=[
                {
                    "s3OriginSource": {
                        "s3BucketSource": bucket,
                        "originAccessIdentity": oai,
                    },
                    "behaviors": [cloudfront.Behavior(is_default_behavior=True)],
                }
            ],
        )

        bucket.grant_read(oai.grant_principal)

        # create table viewer
        TableViewer(self, "UserStatusViewer", title="User Status Table", table=table)

        core.CfnOutput(
            self, id="appurl", value=f"https://{cfd.distribution_domain_name}"
        )
