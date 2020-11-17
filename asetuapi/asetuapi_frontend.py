from aws_cdk import (
    core,
    aws_s3 as s3,
    aws_s3_deployment as s3_dep,
    aws_cloudfront as cloudfront,
)

from os import path


class AsetuapiFrontendStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # deploy application to s3 bucket behind cloudfront
        bucket = s3.Bucket(
            self,
            "ReactAppBucket",
            website_index_document="index.html",
            website_error_document="404.html",
        )

        s3_dep.BucketDeployment(
            self,
            "DeployNextJSReactApp",
            sources=[s3_dep.Source.asset(path.join("client", "out"))],
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

        # only allows cloudfront distribution to read from bucket
        bucket.grant_read(oai.grant_principal)

        core.CfnOutput(
            self, id="appurl", value=f"https://{cfd.distribution_domain_name}"
        )
