#!/usr/bin/env python3.11
import json

from run_common import print_message


def have_parameter_store(settings):
    for pp in settings['ENV_VARIABLES']:
        if 'PARAMETER_STORE' == pp['type']:
            return True

    return False


def use_ecr_image(aws_cli, settings):
    account_id = aws_cli.get_caller_account_id()
    return settings['IMAGE'].startswith(f'{account_id}.dkr.ecr')


def have_cron(settings):
    cc = settings.get('CRON', list())
    return len(cc) > 0


def get_notification_rule(aws_cli, project_arn):
    cmd = ['codestar-notifications', 'list-notification-rules']
    tt = dict()
    tt['Name'] = 'RESOURCE'
    tt['Value'] = project_arn
    cmd += ['--filters', json.dumps([tt])]
    rr = aws_cli.run(cmd)

    if len(rr['NotificationRules']) > 0:
        return rr['NotificationRules'][0]['Arn']


def create_iam_service_role(aws_cli, name):
    role_name = f'codebuild-{name}-service-role'
    if not aws_cli.get_iam_role(role_name):
        print_message(f'create iam service role: {role_name}')

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
        cmd += ['--path', '/service-role/']
        cmd += ['--role-name', role_name]
        cmd += ['--assume-role-policy-document', json.dumps(dd)]
        aws_cli.run(cmd)

    return role_name


def create_managed_secret_iam_policy(aws_cli, name, settings, role_name):
    aws_region = settings['AWS_REGION']

    account_id = aws_cli.get_caller_account_id()

    policy_name = f'CodeBuildManagedSecretPolicy-{name}-{aws_region}'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    if not aws_cli.get_iam_policy(policy_arn):
        print_message(f'create iam policy: {policy_name}')

        dd = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': [
                        'ssm:GetParameters'
                    ],
                    'Resource': [
                        f'arn:aws:ssm:{aws_region}:{account_id}:parameter/CodeBuild/*'
                    ]
                }
            ]
        }

        cmd = ['iam', 'create-policy']
        cmd += ['--policy-name', policy_name]
        cmd += ['--path', '/service-role/']
        cmd += ['--description', 'Policy used in trust relationship with CodeBuild']
        cmd += ['--policy-document', json.dumps(dd)]
        result = aws_cli.run(cmd)

        policy_arn = result['Policy']['Arn']

        cmd = ['iam', 'attach-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-arn', policy_arn]
        aws_cli.run(cmd)


def create_base_iam_policy(aws_cli, name, settings, role_name):
    aws_region = settings['AWS_REGION']

    account_id = aws_cli.get_caller_account_id()

    policy_name = f'CodeBuildBasePolicy-{name}-{aws_region}'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    if not aws_cli.get_iam_policy(policy_arn):
        print_message(f'create iam policy: {policy_name}')

        dd = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Resource': [
                        f'arn:aws:logs:{aws_region}:{account_id}:log-group:/aws/codebuild/{name}',
                        f'arn:aws:logs:{aws_region}:{account_id}:log-group:/aws/codebuild/{name}:*'
                    ],
                    'Action': [
                        'logs:CreateLogGroup',
                        'logs:CreateLogStream',
                        'logs:PutLogEvents'
                    ]
                },
                {
                    'Effect': 'Allow',
                    'Resource': [
                        f'arn:aws:s3:::codepipeline-{aws_region}-*'
                    ],
                    'Action': [
                        's3:PutObject',
                        's3:GetObject',
                        's3:GetObjectVersion',
                        's3:GetBucketAcl',
                        's3:GetBucketLocation'
                    ]
                },
                {
                    'Effect': 'Allow',
                    'Action': [
                        'codebuild:CreateReportGroup',
                        'codebuild:CreateReport',
                        'codebuild:UpdateReport',
                        'codebuild:BatchPutTestCases',
                        'codebuild:BatchPutCodeCoverages'
                    ],
                    'Resource': [
                        f'arn:aws:codebuild:{aws_region}:{account_id}:report-group/{name}-*'
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "ssmmessages:CreateControlChannel",
                        "ssmmessages:CreateDataChannel",
                        "ssmmessages:OpenControlChannel",
                        "ssmmessages:OpenDataChannel"
                    ],
                    "Resource": "*"
                }
            ]
        }

        if 'IAM_POLICY_S3_BUCKET_NAME' in settings:
            pp = {
                'Effect': 'Allow',
                'Action': [
                    's3:DeleteObject',
                    's3:GetObject',
                    's3:ListBucket',
                    's3:PutObject',
                    's3:PutObjectAcl'
                ],
                'Resource': [
                    f"arn:aws:s3:::{settings['IAM_POLICY_S3_BUCKET_NAME']}",
                    f"arn:aws:s3:::{settings['IAM_POLICY_S3_BUCKET_NAME']}/*"
                ]
            }
            dd['Statement'].append(pp)

        if 'S3_OP_BACKUP_BUCKET' in settings:
            pp = {
                'Effect': 'Allow',
                'Action': [
                    "s3:ListBucket",
                    "s3:GetObject",
                    "s3:GetObjectVersion",
                    "s3:GetObjectTagging"
                ],
                'Resource': [
                    f"arn:aws:s3:::{settings['S3_OP_BACKUP_BUCKET']}",
                    f"arn:aws:s3:::{settings['S3_OP_BACKUP_BUCKET']}/*"
                ]
            }
            dd['Statement'].append(pp)

            pp = {
                'Effect': 'Allow',
                'Action': [
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:PutObjectAcl",
                    "s3:PutObjectTagging"
                ],
                'Resource': [
                    f"arn:aws:s3:::hbsmith-backup/{settings['S3_OP_BACKUP_BUCKET']}/*"
                ],
            }
            dd['Statement'].append(pp)

            pp = {
                'Effect': 'Allow',
                'Action': [
                    "s3:ListBucket"
                ],
                'Resource': [
                    "arn:aws:s3:::hbsmith-backup"
                ]
            }
            dd['Statement'].append(pp)

        if 'ARTIFACTS' in settings and settings['ARTIFACTS']['type'] == 'S3':
            pp = {
                'Effect': 'Allow',
                'Action': [
                    's3:PutObject',
                    's3:GetBucketAcl',
                    's3:GetBucketLocation'
                ],
                'Resource': [
                    f"arn:aws:s3:::{settings['ARTIFACTS']['location']}",
                    f"arn:aws:s3:::{settings['ARTIFACTS']['location']}/*"
                ]
            }
            dd['Statement'].append(pp)

        if 'ASSUME_ROLE_ARN' in settings:
            if 'arn:aws:iam' not in settings['ASSUME_ROLE_ARN']:
                print('ERROR! Invalid ARN data')
                raise Exception()

            pp = {
                'Effect': 'Allow',
                'Action': [
                    'sts:AssumeRole'
                ],
                'Resource': [
                    f"{settings['ASSUME_ROLE_ARN']}",
                ]
            }
            dd['Statement'].append(pp)

        cmd = ['iam', 'create-policy']
        cmd += ['--policy-name', policy_name]
        cmd += ['--path', '/service-role/']
        cmd += ['--description', 'Policy used in trust relationship with CodeBuild']
        cmd += ['--policy-document', json.dumps(dd)]
        result = aws_cli.run(cmd)

        policy_arn = result['Policy']['Arn']

        cmd = ['iam', 'attach-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-arn', policy_arn]
        aws_cli.run(cmd)


def create_image_repository_iam_policy(aws_cli, name, settings, role_name):
    aws_region = settings['AWS_REGION']

    account_id = aws_cli.get_caller_account_id()

    policy_name = f'CodeBuildImageRepositoryPolicy-{name}-{aws_region}'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    if not aws_cli.get_iam_policy(policy_arn):
        print_message(f'create iam policy: {policy_name}')

        repo_name = settings['IMAGE'].rstrip(':latest')
        repo_name = repo_name.split('/')[1]

        dd = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': [
                        'ecr:GetAuthorizationToken'
                    ],
                    'Resource': '*'
                },
                {
                    'Effect': 'Allow',
                    'Action': [
                        'ecr:BatchCheckLayerAvailability',
                        'ecr:GetDownloadUrlForLayer',
                        'ecr:BatchGetImage'
                    ],
                    'Resource': f'arn:aws:ecr:{aws_region}:{account_id}:repository/{repo_name}'
                }
            ]
        }

        cmd = ['iam', 'create-policy']
        cmd += ['--policy-name', policy_name]
        cmd += ['--path', '/service-role/']
        cmd += ['--description', 'Policy used in trust relationship with CodeBuild']
        cmd += ['--policy-document', json.dumps(dd)]
        result = aws_cli.run(cmd)

        policy_arn = result['Policy']['Arn']

        cmd = ['iam', 'attach-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-arn', policy_arn]
        aws_cli.run(cmd)


def create_cron_iam_role(aws_cli, name):
    role_name = f'codebuild-{name}-cron-role'
    if not aws_cli.get_iam_role(role_name):
        print_message(f'create iam cron role: {role_name}')

        dd = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {
                        'Service': 'events.amazonaws.com'
                    },
                    'Action': 'sts:AssumeRole'
                }
            ]
        }
        cmd = ['iam', 'create-role']
        cmd += ['--path', '/service-role/']
        cmd += ['--role-name', role_name]
        cmd += ['--assume-role-policy-document', json.dumps(dd)]
        aws_cli.run(cmd)

    return role_name


def create_cron_iam_policy(aws_cli, name, settings, role_name):
    aws_region = settings['AWS_REGION']

    account_id = aws_cli.get_caller_account_id()

    policy_name = f'codebuild-{name}-cron-policy'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    if not aws_cli.get_iam_policy(policy_arn):
        print_message(f'create iam role policy: {policy_name}')

        dd = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': [
                        'codebuild:StartBuild'
                    ],
                    'Resource': [
                        f'arn:aws:codebuild:{aws_region}:{account_id}:project/{name}'
                    ]
                }
            ]
        }

        cmd = ['iam', 'create-policy']
        cmd += ['--policy-name', policy_name]
        cmd += ['--path', '/service-role/']
        cmd += ['--description', 'Policy used in trust relationship with CloudWatchEvents to trigger CodeBuild target']
        cmd += ['--policy-document', json.dumps(dd)]
        result = aws_cli.run(cmd)

        policy_arn = result['Policy']['Arn']

        cmd = ['iam', 'attach-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-arn', policy_arn]
        aws_cli.run(cmd)


def create_cron_event(aws_cli, name, project_arn, schedule_expression, git_branch, role_arn):
    print_message('create cron event')

    cmd = ['events', 'put-rule']
    rule_name = f'{name}CronRuleSourceBy{git_branch.title()}'
    cmd += ['--name', rule_name]
    cmd += ['--schedule-expression', schedule_expression]
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
    cmd += ['--rule', rule_name]
    cmd += ['--targets', target]
    aws_cli.run(cmd)


def create_notification_rule(aws_cli, name, project_arn):
    account_id = aws_cli.get_caller_account_id()

    cmd = ['codestar-notifications', 'create-notification-rule']
    cmd += ['--name', f'codebuild-{name}-notification-rule']
    eid_list = list()
    eid_list.append('codebuild-project-build-state-succeeded')
    eid_list.append('codebuild-project-build-state-stopped')
    eid_list.append('codebuild-project-build-state-failed')
    eid_list.append('codebuild-project-build-state-in-progress')
    cmd += (['--event-type-ids'] + eid_list)
    cmd += ['--resource', project_arn]
    tt = dict()
    aa = f'arn:aws:chatbot::{account_id}:chat-configuration/slack-channel/hbsmith-codebuild-notification'
    tt['TargetAddress'] = aa
    tt['TargetType'] = 'AWSChatbotSlack'
    cmd += ['--targets', json.dumps([tt])]
    cmd += ['--detail-type', 'FULL']
    aws_cli.run(cmd)


def update_notification_rule(aws_cli, name, notification_rule_arn):
    account_id = aws_cli.get_caller_account_id()

    cmd = ['codestar-notifications', 'update-notification-rule']
    cmd += ['--arn', notification_rule_arn]
    cmd += ['--name', f'codebuild-{name}']
    eid_list = list()
    eid_list.append('codebuild-project-build-state-succeeded')
    eid_list.append('codebuild-project-build-state-stopped')
    eid_list.append('codebuild-project-build-state-failed')
    eid_list.append('codebuild-project-build-state-in-progress')
    cmd += (['--event-type-ids'] + eid_list)
    tt = dict()
    aa = f'arn:aws:chatbot::{account_id}:chat-configuration/slack-channel/hbsmith-codebuild-notification'
    tt['TargetAddress'] = aa
    tt['TargetType'] = 'AWSChatbotSlack'
    cmd += ['--targets', json.dumps([tt])]
    cmd += ['--detail-type', 'FULL']
    aws_cli.run(cmd)
