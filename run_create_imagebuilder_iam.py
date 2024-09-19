#!/usr/bin/env python3.11

from run_common import AWSCli
import json
import time

aws_cli = AWSCli()


def create_iam_profile_for_imagebuilder(name):
    profile_name = f'aws-imagebuilder-{name}-instance-profile'
    role_name = 'aws-imagebuilder-role'

    cmd = ['iam', 'get-instance-profile']
    cmd += ['--instance-profile-name', profile_name]
    result = aws_cli.run(cmd, ignore_error=True)

    if result:
        role = result['InstanceProfile']['Roles'][0]
        if role['RoleName'] != role_name:
            raise Exception()

        return profile_name, role['Arn']

    cmd = ['iam', 'create-instance-profile']
    cmd += ['--instance-profile-name', profile_name]
    aws_cli.run(cmd)

    role_file_path = 'file://aws_iam/aws-imagebuilder-role.json'
    cmd = ['iam', 'create-role']
    cmd += ['--path', '/']
    cmd += ['--role-name', role_name]
    cmd += ['--assume-role-policy-document', role_file_path]
    rr = aws_cli.run(cmd)
    role_arn = rr['Role']['Arn']

    cmd = ['iam', 'add-role-to-instance-profile']
    cmd += ['--instance-profile-name', profile_name]
    cmd += ['--role-name', role_name]
    aws_cli.run(cmd)

    cmd = ['iam', 'attach-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore']
    aws_cli.run(cmd)

    cmd = ['iam', 'attach-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/EC2InstanceProfileForImageBuilderECRContainerBuilds']
    aws_cli.run(cmd)

    cmd = ['iam', 'attach-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/EC2InstanceProfileForImageBuilder']
    aws_cli.run(cmd)

    return profile_name, role_arn
