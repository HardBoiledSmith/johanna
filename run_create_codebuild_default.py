#!/usr/bin/env python3
import json
import time

from run_common import AWSCli
from run_common import print_message
from run_create_codebuild_common import create_base_iam_policy
from run_create_codebuild_common import create_iam_service_role
from run_create_codebuild_common import create_managed_secret_iam_policy
from run_create_codebuild_common import have_parameter_store
from run_create_codebuild_common import create_notification_rule
from run_create_codebuild_common import get_notification_rule


def run_create_default_project(name, settings):
    aws_default_region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(aws_default_region)

    git_branch = settings['BRANCH']
    build_spec = settings['BUILD_SPEC']
    build_timeout = settings['BUILD_TIMEOUT']
    compute_type = settings['ENV_COMPUTE_TYPE']
    description = settings['DESCRIPTION']
    git_repo = settings['GITHUB_REPO']
    image = settings['IMAGE']

    ################################################################################
    print_message('check previous version')

    cmd = ['codebuild', 'list-projects']
    result = aws_cli.run(cmd)
    need_update = name in result['projects']

    ################################################################################
    print_message('create iam service role')

    service_role_name = create_iam_service_role(aws_cli, name)
    create_base_iam_policy(aws_cli, name, settings, service_role_name)

    if have_parameter_store(settings):
        create_managed_secret_iam_policy(aws_cli, name, settings, service_role_name)

    time.sleep(10)
    service_role_arn = aws_cli.get_role_arn(service_role_name)

    ################################################################################
    print_message('set environment variable')

    env_list = []
    for pp in settings['ENV_VARIABLES']:
        if 'PARAMETER_STORE' == pp['type']:
            nn = f"/CodeBuild/{name}/{pp['name']}"
            cmd = ['ssm', 'get-parameter', '--name', nn]
            aws_cli.run(cmd)

            pp['value'] = nn

        env_list.append(pp)

    ################################################################################
    config = {
        "name": name,
        "description": description,
        "source": {
            "type": "GITHUB",
            "location": git_repo,
            "gitCloneDepth": 0,
            "buildspec": build_spec,
            "auth": {
                "type": "OAUTH"
            },
            "insecureSsl": True,
            "sourceIdentifier": git_branch
        },
        "artifacts": {
            "type": "NO_ARTIFACTS"
        },
        "cache": {
            "type": "NO_CACHE"
        },
        "environment": {
            "type": "LINUX_CONTAINER",
            "image": image,
            "computeType": compute_type,
            "environmentVariables": env_list
        },
        "serviceRole": service_role_arn,
        "timeoutInMinutes": build_timeout,
        "badgeEnabled": True
    }
    config = json.dumps(config)

    if need_update:
        print_message(f'update project: {name}')
        cmd = ['codebuild', 'update-project', '--cli-input-json', config, '--source-version', git_branch]
        aws_cli.run(cmd)
    else:
        print_message(f'create project: {name}')
        cmd = ['codebuild', 'create-project', '--cli-input-json', config, '--source-version', git_branch]
        aws_cli.run(cmd)

    ################################################################################
    print_message('create slack notification')

    project_arn = result['project']['arn']

    notification_rule_arn = get_notification_rule(aws_cli, project_arn)

    if not notification_rule_arn:
        create_notification_rule(aws_cli, name, project_arn)
    else:
        update_notification_rule(aws_cli, name, notification_rule_arn)
