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


def use_ecr_image(aws_cli, settings):
    account_id = aws_cli.get_caller_account_id()
    return settings['IMAGE'].startswith(f'{account_id}.dkr.ecr')


def have_cron(settings):
    cc = settings.get('CRON', list())
    return len(cc) > 0


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


def create_secret_manager_iam_policy(aws_cli, name, settings, role_name):
    aws_region = settings['AWS_DEFAULT_REGION']

    policy_name = f'CodeBuildSecretsManagerPolicy-{name}-{aws_region}'
    if not aws_cli.get_iam_role_policy(role_name, policy_name):
        print_message(f'create iam role policy: {policy_name}')

        account_id = aws_cli.get_caller_account_id()

        dd = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': [
                        'secretsmanager:GetSecretValue'
                    ],
                    'Resource': [
                        f'arn:aws:secretsmanager:{aws_region}:{account_id}:secret:/CodeBuild/*'
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
    aws_region = settings['AWS_DEFAULT_REGION']

    policy_name = f'CodeBuildBasePolicy-{name}-{aws_region}'
    if not aws_cli.get_iam_role_policy(role_name, policy_name):
        print_message(f'create iam role policy: {policy_name}')

        account_id = aws_cli.get_caller_account_id()

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
                }
            ]
        }

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
    aws_region = settings['AWS_DEFAULT_REGION']

    policy_name = f'CodeBuildImageRepositoryPolicy-{name}-{aws_region}'
    if not aws_cli.get_iam_role_policy(role_name, policy_name):
        print_message(f'create iam role policy: {policy_name}')

        account_id = aws_cli.get_caller_account_id()

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
                        'ecr:BatchGetImage',
                        'ecr:PutImage',
                        'ecr:InitiateLayerUpload',
                        'ecr:UploadLayerPart',
                        'ecr:CompleteLayerUpload'
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


def create_iam_cron_role(aws_cli, name, settings):
    aws_region = settings['AWS_DEFAULT_REGION']

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

    policy_name = f'codebuild-{name}-cron-policy'
    if not aws_cli.get_iam_role_policy(role_name, policy_name):
        print_message(f'create iam role policy: {policy_name}')

        account_id = aws_cli.get_caller_account_id()

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

    return role_name


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


def run_create_codebuild_github(name, settings):
    aws_default_region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(aws_default_region)

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
    print_message('create project iam role')

    service_role_name = create_iam_service_role(aws_cli, name)
    create_base_iam_policy(aws_cli, name, settings, service_role_name)

    if have_parameter_store(settings):
        create_secret_manager_iam_policy(aws_cli, name, settings, service_role_name)

    if use_ecr_image(aws_cli, settings):
        create_image_repository_iam_policy(aws_cli, name, settings, service_role_name)

    time.sleep(5)
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
        cron_role_name = create_iam_cron_role(aws_cli, name, settings)

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

    if need_update:
        cmd = ['codebuild', 'update-webhook', '--cli-input-json', config]
        aws_cli.run(cmd)
    else:
        cmd = ['codebuild', 'create-webhook', '--cli-input-json', config]
        aws_cli.run(cmd)
