#!/usr/bin/env python3
import json

from run_common import AWSCli
from run_common import print_message


def run_create_codebuild_github(name, settings):
    aws_cli = AWSCli()

    git_branch = settings['BRANCH']
    build_spec = settings['BUILD_SPEC']
    build_timeout = settings['BUILD_TIMEOUT']
    compute_type = settings['ENV_COMPUTE_TYPE']
    description = settings['DESCRIPTION']
    git_repo = settings['GITHUB_REPO']
    github_token = settings['GITHUB_TOKEN']
    image = settings['IMAGE']
    container_type = 'LINUX_CONTAINER'
    if 'window' in image:
        container_type = 'WINDOWS_CONTAINER'

    artifacts = {"type": "NO_ARTIFACTS"}
    if 'ARTIFACTS' in settings:
        artifacts = settings['ARTIFACTS']

    ################################################################################
    print_message('check previous version')

    cmd = ['codebuild', 'list-projects']
    result = aws_cli.run(cmd)
    need_update = name in result['projects']
    ################################################################################
    role_arn = aws_cli.get_role_arn('aws-codebuild-secure-parameter-role')

    ################################################################################
    print_message('set environment variable')

    env_list = []

    for pp in settings['ENV_VARIABLES']:
        if 'PARAMETER_STORE' == pp['type']:
            nn = '/CodeBuild/%s/%s' % (name, pp['name'])
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
                "type": "OAUTH",
                "resource": github_token
            },
            "insecureSsl": True,
            "sourceIdentifier": git_branch
        },
        "artifacts": artifacts,
        "cache": {
            "type": "NO_CACHE"
        },
        "environment": {
            "type": container_type,
            "image": image,
            "computeType": compute_type,
            "environmentVariables": env_list
        },
        "serviceRole": role_arn,
        "timeoutInMinutes": build_timeout,
        "badgeEnabled": True
    }

    config = json.dumps(config)

    if need_update:
        print_message('update project: %s' % name)

        cmd = ['codebuild', 'update-project', '--cli-input-json', config]
        aws_cli.run(cmd)
        return

    print_message('create project: %s' % name)

    cmd = ['codebuild', 'create-project', '--cli-input-json', config]
    aws_cli.run(cmd)

    config = {
        "projectName": name,
        "filterGroups": [
            [
                {
                    "excludeMatchedPattern": False,
                    "pattern": "PUSH, PULL_REQUEST_CREATED",
                    "type": "EVENT"
                }
            ]
        ]
    }
    config = json.dumps(config)
    cmd = ['codebuild', 'create-webhook', '--cli-input-json', config]
    aws_cli.run(cmd)
