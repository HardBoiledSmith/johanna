#!/usr/bin/env python3.12
from run_common import AWSCli
from run_common import print_message


def terminate_iam_profile_for_imagebuilder(name):
    print_message('delete imagebuilder iam')

    aws_cli = AWSCli()

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
