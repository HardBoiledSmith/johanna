#!/usr/bin/env python3
import json

from run_common import AWSCli
from run_common import print_message


def run_create_codebuild_default(name, settings):
    aws_cli = AWSCli()

    git_branch = settings['BRANCH']
    build_spec = settings['BUILD_SPEC']
    build_timeout = settings['BUILD_TIMEOUT']
    compute_type = settings['ENV_COMPUTE_TYPE']
    description = settings['DESCRIPTION']
    env_list = settings['ENV_VARIABLES']
    git_repo = settings['GITHUB_REPO']
    github_token = settings['GITHUB_TOKEN']
    image = settings['IMAGE']

    ################################################################################
    print_message('check previous version')

    cmd = ['codebuild', 'list-projects']
    result = aws_cli.run(cmd)
    need_update = name in result['projects']
    ################################################################################
    role_arn = aws_cli.get_role_arn('aws-codebuild-default-role')

    config = {
        "name": name,
        "description": description,
        "source": {
            "type": "GITHUB_ENTERPRISE",
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
