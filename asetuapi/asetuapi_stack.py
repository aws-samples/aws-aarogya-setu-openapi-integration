from aws_cdk import (
    core,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_dynamodb as ddb,
    aws_sqs as sqs,
    aws_lambda_event_sources as events,
    aws_cognito as cognito,
    aws_secretsmanager as secretsmanager,
)
from os import path

API_NAME = "asetuapipoc"


class AsetuapiStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        api_secret = secretsmanager.Secret.from_secret_complete_arn(
            self,
            "ApiSecret",
            secret_complete_arn="arn:aws:secretsmanager:ap-south-1:669807167988:secret:asetuapisecrets-6Dnp0z",
        )

        # create auth
        user_pool = cognito.UserPool(
            self,
            "AppUserPool",
            self_sign_up_enabled=True,
            account_recovery=cognito.AccountRecovery.PHONE_AND_EMAIL,
            user_verification=cognito.VerificationEmailStyle.CODE,
            auto_verify={"email": True},
            standard_attributes={"email": {"required": True, "mutable": True}},
        )

        user_pool_client = cognito.UserPoolClient(
            self, "UserPoolClient", user_pool=user_pool
        )

        # Create storage and queue
        bulk_request_queue = sqs.Queue(
            self,
            "BulkRequestQueue",
        )

        user_status_table = ddb.Table(
            self,
            "UserStatusTable",
            partition_key={"name": "mobile_number", "type": ddb.AttributeType.STRING},
            time_to_live_attribute="expdate",
        )
        self._user_status_table = user_status_table

        requests_table = ddb.Table(
            self,
            "RequestsTable",
            partition_key={"name": "mobile_number", "type": ddb.AttributeType.STRING},
            time_to_live_attribute="expdate",
        )

        # Create layer for lambda run time dependencies
        dependency_layer = _lambda.LayerVersion(
            self,
            "PythonDependencies",
            code=_lambda.Code.from_asset(path.join("lambda", "dependency-layer.zip")),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_7],
            description="The layer contains requests and pyjwt dependencies",
        )

        # Create Lambda functions
        single_request = _lambda.Function(
            self,
            "SingleRequesetHandler",
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.Code.asset("lambda"),
            handler="single_request.handler",
            timeout=core.Duration.seconds(10),
            layers=[dependency_layer],
            environment={
                "USER_STATUS_TABLE": user_status_table.table_name,
                "REQUESTS_TABLE": requests_table.table_name,
                "API_SECRET_ARN": api_secret.secret_full_arn,
            },
        )

        # give lambda access permissions to ddb tables and secrets
        user_status_table.grant_read_write_data(single_request)
        requests_table.grant_read_write_data(single_request)
        api_secret.grant_read(single_request)

        bulk_request = _lambda.Function(
            self,
            "BulkRequestHandler",
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.Code.asset("lambda"),
            handler="bulk_request.handler",
            timeout=core.Duration.seconds(30),
            environment={
                "QUEUE_URL": bulk_request_queue.queue_url,
            },
        )

        # give lambda access to write to queue
        bulk_request_queue.grant_send_messages(bulk_request)

        queue_receiver = _lambda.Function(
            self,
            "QueueReceiverHandler",
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.Code.asset("lambda"),
            handler="queue_receiver.handler",
            timeout=core.Duration.seconds(10),
            layers=[dependency_layer],
            environment={
                "USER_STATUS_TABLE": user_status_table.table_name,
                "REQUESTS_TABLE": requests_table.table_name,
                "QUEUE_URL": bulk_request_queue.queue_url,
                "API_SECRET_ARN": api_secret.secret_full_arn,
            },
        )

        # lambda gets triggered by sqs queue and writes to both tables
        queue_receiver.add_event_source(
            events.SqsEventSource(bulk_request_queue, batch_size=1)
        )

        # give queue receiver access to tables, queue and secrets
        bulk_request_queue.grant_consume_messages(queue_receiver)
        user_status_table.grant_read_write_data(queue_receiver)
        requests_table.grant_read_write_data(queue_receiver)

        api_secret.grant_read(queue_receiver)

        scan_table = _lambda.Function(
            self,
            "ScanTableHandler",
            runtime=_lambda.Runtime.PYTHON_3_7,
            code=_lambda.Code.asset("lambda"),
            handler="scan_table.handler",
            timeout=core.Duration.seconds(30),
            environment={
                "USER_STATUS_TABLE": user_status_table.table_name,
            },
        )

        user_status_table.grant_read_data(scan_table)

        # create api endpoints with authorization
        api = apigw.RestApi(
            self,
            "ASetuApiGateway",
            rest_api_name=API_NAME,
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS
            ),
        )

        auth = apigw.CfnAuthorizer(
            self,
            "ApiCognitoAuthorizer",
            name="CognitoAuthorizer",
            type="COGNITO_USER_POOLS",
            authorizer_result_ttl_in_seconds=300,
            identity_source="method.request.header.Authorization",
            rest_api_id=api.rest_api_id,
            provider_arns=[user_pool.user_pool_arn],
        )

        single_request_integration = apigw.LambdaIntegration(single_request, proxy=True)
        single_request_resource = api.root.add_resource("status")
        single_method = single_request_resource.add_method(
            "POST",
            single_request_integration,
            api_key_required=False,
            authorizer=auth,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        bulk_request_integration = apigw.LambdaIntegration(bulk_request, proxy=True)
        bulk_request_resource = api.root.add_resource("bulk_status")
        bulk_method = bulk_request_resource.add_method(
            "POST",
            bulk_request_integration,
            api_key_required=False,
            authorizer=auth,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        scan_table_integration = apigw.LambdaIntegration(scan_table, proxy=True)
        scan_table_resource = api.root.add_resource("scan")
        scan_method = scan_table_resource.add_method(
            "GET",
            scan_table_integration,
            api_key_required=False,
            authorizer=auth,
            authorization_type=apigw.AuthorizationType.COGNITO,
        )

        # Override authorizer to use COGNITO to authorize apis
        # Solution from: https://github.com/aws/aws-cdk/issues/9023#issuecomment-658309644
        methods = [single_method, bulk_method, scan_method]
        for method in methods:
            method.node.find_child("Resource").add_property_override(
                "AuthorizationType", "COGNITO_USER_POOLS"
            )
            method.node.find_child("Resource").add_property_override(
                "AuthorizerId", {"Ref": auth.logical_id}
            )

        # Export output values for frontend application
        core.CfnOutput(
            self,
            "user-pool-id",
            value=user_pool.user_pool_id,
            export_name="USER-POOL-ID",
        )
        core.CfnOutput(
            self,
            "user-pool-web-client",
            value=user_pool_client.user_pool_client_id,
            export_name="WEB-CLIENT-ID",
        )
        core.CfnOutput(
            self, "api-endpoint-url", value=api.url, export_name="API-ENDPOINT-URL"
        )
        core.CfnOutput(
            self,
            "deployment-region",
            value=self.region,
            export_name="REGION",
        )
        core.CfnOutput(
            self, "stack-name", value=self.stack_name, export_name="STACK-NAME"
        )
