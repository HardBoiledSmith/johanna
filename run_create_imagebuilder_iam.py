#!/usr/bin/env python3

from run_common import AWSCli
import json
import time

aws_cli = AWSCli()


def create_iam_profile_for_imagebuilder(name):
    profile_name = f'aws-imagebuilder-{name}-instance-profile'
    role_name = 'aws-imagebuilder-role'
    s3_logging_policy_name = 'aws-imagebuilder-s3-put-ojbect-policy'

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

    pp = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject"
                ],
                "Resource": "*"
            }
        ]
    }

    cmd = ['iam', 'create-policy']
    cmd += ['--policy-name', s3_logging_policy_name]
    cmd += ['--path', '/']
    cmd += ['--description', 'Policy for uploading logs generated during build to s3']
    cmd += ['--policy-document', json.dumps(pp)]
    rr = aws_cli.run(cmd)
    time.sleep(10)

    s3_policy_arn = rr['Policy']['Arn']
    cmd = ['iam', 'attach-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-arn', s3_policy_arn]
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
