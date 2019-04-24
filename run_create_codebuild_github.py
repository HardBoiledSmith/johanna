#!/usr/bin/env python3
import json
import time

from run_common import AWSCli
from run_common import print_message


def have_parameter_store(settings):
    for pp in settings['ENV_VARIABLES']:
        if 'PARAMETER_STORE' == pp['type']:
            return True

    return False


def create_iam_for_codebuild(name, settings):
    aws_cli = AWSCli()

    nn = name.replace('_', '-')
    role_name = 'aws-codebuild-%s-role' % nn
    if not aws_cli.get_iam_role(role_name):
        print_message('create iam role: %s' % role_name)

        dd = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {
                        'Service': 'codebuild.amazonaws.com'
                    },
                    'Action': 'sts:AssumeRole'
                }
            ]
        }
        cmd = ['iam', 'create-role']
        cmd += ['--role-name', role_name]
        cmd += ['--assume-role-policy-document', json.dumps(dd)]
        aws_cli.run(cmd)

    policy_name = 'aws-codebuild-%s-policy' % nn
    if not aws_cli.get_iam_role_policy(role_name, policy_name):
        print_message('create iam role policy: %s' % policy_name)

        dd = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': [
                        'logs:CreateLogGroup',
                        'logs:CreateLogStream',
                        'logs:PutLogEvents'
                    ],
                    'Resource': '*'
                }
            ]
        }

        if 'ARTIFACTS' in settings \
                and settings['ARTIFACTS']['type'] == 'S3':
            pp = {
                'Effect': 'Allow',
                'Action': ['s3:PutObject'],
                'Resource': 'arn:aws:s3:::%s/*' % settings['ARTIFACTS']['location']
            }
            dd['Statement'].append(pp)

        if have_parameter_store(settings):
            pp = {
                'Action': 'ssm:GetParameters',
                'Effect': 'Allow',
                'Resource': 'arn:aws:ssm:ap-northeast-2:*:parameter/CodeBuild/*'
            }
            dd['Statement'].append(pp)

        cmd = ['iam', 'put-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-name', policy_name]
        cmd += ['--policy-document', json.dumps(dd)]
        aws_cli.run(cmd)
        time.sleep(120)

    return role_name


def run_create_codebuild_github(name, settings):
    aws_default_region = settings.get('AWS_DEFAULT_REGION')
    aws_cli = AWSCli(aws_default_region)

    git_branch = settings['BRANCH']
    build_spec = settings['BUILD_SPEC']
    build_timeout = settings['BUILD_TIMEOUT']
    compute_type = settings['ENV_COMPUTE_TYPE']
    description = settings['DESCRIPTION']
    git_repo = settings['GITHUB_REPO']
    github_token = settings['GITHUB_TOKEN']
    image = settings['IMAGE']
    container_type = settings.get('CONTAINER_TYPE', 'LINUX_CONTAINER')
    artifacts = settings.get('ARTIFACTS', {'type': 'NO_ARTIFACTS'})

    ################################################################################
    print_message('check previous version')

    cmd = ['codebuild', 'list-projects']
    result = aws_cli.run(cmd)
    need_update = name in result['projects']
    ################################################################################
    role_name = create_iam_for_codebuild(name, settings)
    role_arn = aws_cli.get_role_arn(role_name)

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
        'name': name,
        'description': description,
        'source': {
            'type': 'GITHUB',
            'location': git_repo,
            'gitCloneDepth': 0,
            'buildspec': build_spec,
            'auth': {
                'type': 'OAUTH',
                'resource': github_token
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
        'serviceRole': role_arn,
        'timeoutInMinutes': build_timeout,
        'badgeEnabled': True
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
    cmd = ['codebuild', 'create-webhook', '--cli-input-json', config]
    aws_cli.run(cmd)
