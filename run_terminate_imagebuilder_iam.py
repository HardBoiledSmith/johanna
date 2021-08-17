#!/usr/bin/env python3
from run_common import AWSCli


def terminate_iam_profile_for_imagebuilder(name):
    aws_cli = AWSCli()

    account_id = aws_cli.get_caller_account_id()
    role_name = 'aws-imagebuilder-role'
    policy_name = 'aws-imagebuilder-s3-put-ojbect-policy'

    cmd = ['iam', 'delete-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-name', policy_name]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'detach-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/EC2InstanceProfileForImageBuilderECRContainerBuilds']
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'detach-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/EC2InstanceProfileForImageBuilder']
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'detach-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore']
    aws_cli.run(cmd, ignore_error=True)

    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/aws-imagebuilder-s3-put-ojbect-policy'
    cmd = ['iam', 'detach-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-arn', policy_arn]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'delete-policy']
    cmd += ['--policy-arn', policy_arn]
    aws_cli.run(cmd, ignore_error=True)

    profile_name = f'aws-imagebuilder-{name}-instance-profile'

    cmd = ['iam', 'remove-role-from-instance-profile']
    cmd += ['--instance-profile-name', profile_name]
    cmd += ['--role-name', role_name]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'delete-instance-profile']
    cmd += ['--instance-profile-name', profile_name]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'delete-role']
    cmd += ['--role-name', role_name]
    aws_cli.run(cmd, ignore_error=True)


terminate_iam_profile_for_imagebuilder('gendo')
