#!/usr/bin/env python3
from run_common import AWSCli
from run_common import print_message


def terminate_iam_for_codebuild(codebuild_type):
    _aws_cli = AWSCli()
    role_name = f'aws-codebuild-{codebuild_type}-role'
    policy_name = f'aws-codebuild-{codebuild_type}-policy'

    print_message('delete iam role policy %s' % policy_name)

    cmd = ['iam', 'delete-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-name', policy_name]
    _aws_cli.run(cmd, ignore_error=True)

    print_message('delete iam role %s' % role_name)

    cmd = ['iam', 'delete-role']
    cmd += ['--role-name', role_name]
    _aws_cli.run(cmd, ignore_error=True)


def run_terminate_vpc_codebuild(name):
    print_message('delete github codebuild %s' % name)

    print_message('delete github codebuild(webhook) %s' % name)

    _aws_cli = AWSCli()
    print_message('delete github codebuild(project) %s' % name)

    cmd = ['codebuild', 'delete-project']
    cmd += ['--name', name]
    _aws_cli.run(cmd, ignore_error=True)

    print_message('delete github codebuild(environment variable) %s' % name)

    cmd = ['ssm', 'get-parameters-by-path']
    cmd += ['--path', '/CodeBuild/%s' % name]

    result = _aws_cli.run(cmd)
    if 'Parameters' in result:
        for rr in result['Parameters']:
            cmd = ['ssm', 'delete-parameter']
            cmd += ['--name', rr['Name']]
            _aws_cli.run(cmd, ignore_error=True)

    terminate_iam_for_codebuild(name.replace('_', '-'))
