#!/usr/bin/env python3
from run_common import AWSCli
from run_common import print_message


def terminate_all_iam_role_and_policy(aws_cli, name, settings):
    aws_region = settings['AWS_DEFAULT_REGION']

    account_id = aws_cli.get_caller_account_id()

    pa_list = list()

    policy_name = f'CodeBuildBasePolicy-{name}-{aws_region}'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    pa_list.append(policy_arn)

    policy_name = f'CodeBuildManagedSecretPolicy-{name}-{aws_region}'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    pa_list.append(policy_arn)

    policy_name = f'CodeBuildImageRepositoryPolicy-{name}-{aws_region}'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    pa_list.append(policy_arn)

    policy_name = f'CodeBuildVpcPolicy-{name}-{aws_region}'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    pa_list.append(policy_arn)

    policy_name = f'codebuild-{name}-cron-policy'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    pa_list.append(policy_arn)

    for pa in pa_list:
        print_message(f'detach iam policy: {pa}')

        cmd = ['iam', 'detach-role-policy']
        cmd += ['--role-name', f'codebuild-{name}-service-role']
        cmd += ['--policy-arn', pa]
        aws_cli.run(cmd, ignore_error=True)

        cmd = ['iam', 'detach-role-policy']
        cmd += ['--role-name', f'codebuild-{name}-cron-role']
        cmd += ['--policy-arn', pa]
        aws_cli.run(cmd, ignore_error=True)

        print_message(f'delete iam policy: {pa}')

        cmd = ['iam', 'delete-policy']
        cmd += ['--policy-arn', pa]
        aws_cli.run(cmd, ignore_error=True)

    rn_list = list()

    rn_list.append(f'codebuild-{name}-service-role')
    rn_list.append(f'codebuild-{name}-cron-role')

    for rn in rn_list:
        print_message(f'delete iam role: {rn}')

        cmd = ['iam', 'delete-role']
        cmd += ['--role-name', rn]
        aws_cli.run(cmd, ignore_error=True)


def run_terminate_vpc_project(name, settings):
    aws_default_region = settings['AWS_DEFAULT_REGION']

    print_message(f'delete vpc project: {name}')

    aws_cli = AWSCli(aws_default_region)

    cmd = ['codebuild', 'delete-project']
    cmd += ['--name', name]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['ssm', 'get-parameters-by-path']
    cmd += ['--path', '/CodeBuild/%s' % name]
    result = aws_cli.run(cmd)

    for rr in result.get('Parameters', list()):
        cmd = ['ssm', 'delete-parameter']
        cmd += ['--name', rr['Name']]
        aws_cli.run(cmd, ignore_error=True)

    terminate_all_iam_role_and_policy(aws_cli, name, settings)
