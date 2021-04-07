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
    aws_default_region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli()

    nn = name.replace('_', '-')
    role_name = f'aws-codebuild-{nn}-role'
    if not aws_cli.get_iam_role(role_name):
        print_message(f'create iam role: {role_name}')

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

    policy_name = f'aws-codebuild-{nn}-policy'
    if not aws_cli.get_iam_role_policy(role_name, policy_name):
        print_message(f'create iam role policy: {policy_name}')

        account_id = aws_cli.get_caller_account_id()

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
                    'Resource': [
                        f'arn:aws:logs:{aws_default_region}:{account_id}:log-group:/aws/codebuild/{name}',
                        f'arn:aws:logs:{aws_default_region}:{account_id}:log-group:/aws/codebuild/{name}:*'
                    ]
                }
            ]
        }

        if 'ARTIFACTS' in settings \
                and settings['ARTIFACTS']['type'] == 'S3':
            pp = {
                'Effect': 'Allow',
                'Action': ['s3:PutObject'],
                'Resource': f"arn:aws:s3:::{settings['ARTIFACTS']['location']}/*"
            }
            dd['Statement'].append(pp)

        if have_parameter_store(settings):
            pp = {
                'Action': 'ssm:GetParameters',
                'Effect': 'Allow',
                'Resource': f'arn:aws:ssm:{aws_default_region}:{account_id}:parameter/CodeBuild/{name}/*'
            }
            dd['Statement'].append(pp)

        pp = {
            'Action': 'codebuild:StartBuild',
            'Effect': 'Allow',
            'Resource': f'arn:aws:codebuild:{aws_default_region}:{account_id}:project/CodeBuild/{name}'
        }
        dd['Statement'].append(pp)

        cmd = ['iam', 'put-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-name', policy_name]
        cmd += ['--policy-document', json.dumps(dd)]
        aws_cli.run(cmd)

        print_message('wait 120 seconds to let iam role and policy propagated to all regions...')
        time.sleep(120)

    return role_name


def run_create_codebuild_cron(name, settings):
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
    role_name = create_iam_for_codebuild(name, settings)
    role_arn = aws_cli.get_role_arn(role_name)

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
        "serviceRole": role_arn,
        "timeoutInMinutes": build_timeout,
        "badgeEnabled": True
    }
    config = json.dumps(config)

    if need_update:
        print_message(f'update project: {name}')

        cmd = ['codebuild', 'update-project', '--cli-input-json', config, '--source-version', git_branch]
        aws_cli.run(cmd)

        print_message('update cron event')

        cmd = ['events', 'put-rule']
        cmd += ['--name', name + 'CronRule']
        cmd += ['--schedule-expression', settings['SCHEDULE_EXPRESSION']]
        aws_cli.run(cmd)
        return

    print_message(f'create project: {name}')

    cmd = ['codebuild', 'create-project', '--cli-input-json', config, '--source-version', git_branch]
    result = aws_cli.run(cmd)

    project_arn = result['project']['arn']

    print_message('create cron event')

    cmd = ['events', 'put-rule']
    cmd += ['--name', name + 'CronRule']
    cmd += ['--schedule-expression', settings['SCHEDULE_EXPRESSION']]
    aws_cli.run(cmd)

    print_message('link event and codebuild project')

    target_input = {
        "sourceVersion": git_branch
    }
    target_input = json.dumps(target_input)

    target = {
        "Id": "1",
        "Arn": project_arn,
        "RoleArn": role_arn,
        "Input": target_input
    }
    target = json.dumps(target)

    cmd = ['events', 'put-targets']
    cmd += ['--rule', name + 'CronRule']
    cmd += ['--targets', target]
    aws_cli.run(cmd)
