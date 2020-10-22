from aws_cdk.core import Stack, StackProps, Construct, SecretValue
from aws_cdk.pipelines import CdkPipeline, SimpleSynthAction
from aws_cdk.aws_codecommit import Repository

import aws_cdk.aws_codepipeline as codepipeline
import aws_cdk.aws_codepipeline_actions as codepipeline_actions


class DeployPipelineStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        source_artifact = codepipeline.Artifact()
        cloud_assembly_artifact = codepipeline.Artifact()

        pipeline = CdkPipeline(
            self,
            "Pipeline",
            pipeline_name="DeployPipeline",
            cloud_assembly_artifact=cloud_assembly_artifact,
            source_action=codepipeline_actions.CodeCommitSourceAction(
                action_name="DeployApi",
                output=source_artifact,
                repository=Repository.from_repository_name(
                    self, "AsetuAPIRepository", repository_name="asetuapi"
                ),
                branch="master",
                trigger=codepipeline_actions.CodeCommitTrigger.POLL,
            ),
            synth_action=SimpleSynthAction.standard_npm_synth(
                source_artifact=source_artifact,
                cloud_assembly_artifact=cloud_assembly_artifact,
                build_command="npm run build --prefix client",
            ),
        )
