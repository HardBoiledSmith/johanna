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
    git_repo = settings['GITHUB_REPO']
    image = settings['IMAGE']

    ################################################################################
    print_message('check previous version')

    cmd = ['codebuild', 'list-projects']
    result = aws_cli.run(cmd)
    need_update = name in result['projects']
    ################################################################################
    print_message('set environment variable')

    env_list = []
    is_exist_parameter_store = False

    for pp in settings['ENV_VARIABLES']:
        if 'PARAMETER_STORE' == pp['type']:
            is_exist_parameter_store = True
            nn = '/CodeBuild/%s/%s' % (name, pp['name'])
            cmd = ['ssm', 'get-parameter', '--name', nn]
            aws_cli.run(cmd)

            pp['value'] = nn

        env_list.append(pp)

    role_arn = aws_cli.get_role_arn('aws-codebuild-default-role')
    if is_exist_parameter_store:
        role_arn = aws_cli.get_role_arn('aws-codebuild-secure-parameter-role')

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
