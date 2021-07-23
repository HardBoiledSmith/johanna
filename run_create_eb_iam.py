#!/usr/bin/env python3

from run_common import AWSCli

aws_cli = AWSCli()


def create_iam_profile_for_ec2_instances(template_path, name):
    profile_name = f'aws-elasticbeanstalk-{name}-instance-profile'
    cmd = ['iam', 'create-instance-profile']
    cmd += ['--instance-profile-name', profile_name]
    aws_cli.run(cmd)

    role_name = f'aws-elasticbeanstalk-{name}-ec2-role'
    role_file_path = f'file://{template_path}/{name}/_provisioning/iam/aws-elasticbeanstalk-ec2-role.json'
    cmd = ['iam', 'create-role']
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
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier']
    aws_cli.run(cmd)

    cmd = ['iam', 'attach-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore']
    aws_cli.run(cmd)

    policy_name = f'aws-elasticbeanstalk-{name}-ec2-policy'
    policy_file_path = f'file://{template_path}/{name}/_provisioning/iam/aws-elasticbeanstalk-ec2-policy.json'
    cmd = ['iam', 'put-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-name', policy_name]
    cmd += ['--policy-document', policy_file_path]
    aws_cli.run(cmd)

    return profile_name, role_arn
