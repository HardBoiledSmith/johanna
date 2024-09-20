#!/usr/bin/env python3.11
import json
import time

from run_common import AWSCli
from run_common import print_message
from run_create_codebuild_common import create_base_iam_policy
from run_create_codebuild_common import create_cron_event
from run_create_codebuild_common import create_cron_iam_policy
from run_create_codebuild_common import create_cron_iam_role
from run_create_codebuild_common import create_iam_service_role
from run_create_codebuild_common import create_image_repository_iam_policy
from run_create_codebuild_common import create_managed_secret_iam_policy
from run_create_codebuild_common import create_notification_rule
from run_create_codebuild_common import get_notification_rule
from run_create_codebuild_common import have_cron
from run_create_codebuild_common import have_parameter_store
from run_create_codebuild_common import update_notification_rule
from run_create_codebuild_common import use_ecr_image


def run_create_github_project(name, settings):
    aws_cli = AWSCli(settings['AWS_REGION'])

    git_branch = settings['BRANCH']
    build_spec = settings['BUILD_SPEC']
    build_timeout = settings['BUILD_TIMEOUT']
    compute_type = settings['ENV_COMPUTE_TYPE']
    description = settings['DESCRIPTION']
    git_repo = settings['GITHUB_REPO']
    image = settings['IMAGE']
    container_type = settings.get('CONTAINER_TYPE', 'LINUX_CONTAINER')
    artifacts = settings.get('ARTIFACTS', {'type': 'NO_ARTIFACTS'})

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

    if use_ecr_image(aws_cli, settings):
        create_image_repository_iam_policy(aws_cli, name, settings, service_role_name)

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
        'name': name,
        'description': description,
        'source': {
            'type': 'GITHUB',
            'location': git_repo,
            'gitCloneDepth': 0,
            'buildspec': build_spec,
            'auth': {
                'type': 'OAUTH'
            },
            'insecureSsl': True,
            'sourceIdentifier': git_branch
        },
        'artifacts': artifacts,
        'cache': {
            'type': 'NO_CACHE'
        },
        'environment': {
            'type': container_type,
            'image': image,
            'computeType': compute_type,
            'environmentVariables': env_list
        },
        'serviceRole': service_role_arn,
        'timeoutInMinutes': build_timeout,
        'badgeEnabled': True
    }
    if 'SECONDARY_ARTIFACTS' in settings:
        config['secondaryArtifacts'] = settings['SECONDARY_ARTIFACTS']
    if use_ecr_image(aws_cli, settings):
        config['environment']['imagePullCredentialsType'] = 'SERVICE_ROLE'

    config = json.dumps(config)

    if need_update:
        print_message(f'update project: {name}')
        cmd = ['codebuild', 'update-project', '--cli-input-json', config, '--source-version', git_branch]
        result = aws_cli.run(cmd)
    else:
        print_message(f'create project: {name}')
        cmd = ['codebuild', 'create-project', '--cli-input-json', config, '--source-version', git_branch]
        result = aws_cli.run(cmd)

    ################################################################################
    print_message('create cron trigger iam role and trigger')

    if have_cron(settings):
        cron_role_name = create_cron_iam_role(aws_cli, name)
        create_cron_iam_policy(aws_cli, name, settings, cron_role_name)

        time.sleep(5)
        cron_role_arn = aws_cli.get_role_arn(cron_role_name)

        for cc in settings['CRON']:
            project_arn = result['project']['arn']
            se = cc['SCHEDULE_EXPRESSION']
            sv = cc['SOURCE_VERSION']
            create_cron_event(aws_cli, name, project_arn, se, sv, cron_role_arn)

    ################################################################################
    print_message('create github webhook')

    config = {
        'projectName': name,
        'filterGroups': [
            [
                {
                    'excludeMatchedPattern': False,
                    'pattern': 'PUSH, PULL_REQUEST_CREATED',
                    'type': 'EVENT'
                }
            ]
        ]
    }
    config = json.dumps(config)

    if 'webhook' in result['project']:
        cmd = ['codebuild', 'update-webhook', '--cli-input-json', config]
        aws_cli.run(cmd)
    else:
        cmd = ['codebuild', 'create-webhook', '--cli-input-json', config]
        aws_cli.run(cmd)

    ################################################################################
    print_message('create slack notification')

    project_arn = result['project']['arn']

    notification_rule_arn = get_notification_rule(aws_cli, project_arn)

    if not notification_rule_arn:
        create_notification_rule(aws_cli, name, project_arn)
    else:
        update_notification_rule(aws_cli, name, notification_rule_arn)
