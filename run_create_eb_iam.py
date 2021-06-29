#!/usr/bin/env python3

from run_common import print_message
from run_common import AWSCli

aws_cli = AWSCli()


def create_iam_for_eb(name):
    instance_profile_name = f'aws-elasticbeanstalk-{name}-ec2-role'
    instance_profile_policy_name = f'aws-elasticbeanstalk-{name}-ec2-policy'
    dotfile_path = f'template/{name}/{name}/_provisioning/.johanna'

    if not aws_cli.get_iam_role(instance_profile_name):
        print_message(f'create iam: {instance_profile_name}')

        cmd = ['iam', 'create-instance-profile']
        cmd += ['--instance-profile-name', instance_profile_name]
        aws_cli.run(cmd)

        cmd = ['iam', 'create-role']
        cmd += ['--role-name', instance_profile_name]
        cmd += ['--assume-role-policy-document', f'file://{dotfile_path}/instance-profile/role.json']
        aws_cli.run(cmd)

        cmd = ['iam', 'add-role-to-instance-profile']
        cmd += ['--instance-profile-name', instance_profile_name]
        cmd += ['--role-name', instance_profile_name]
        aws_cli.run(cmd)

        cmd = ['iam', 'attach-role-policy']
        cmd += ['--role-name', instance_profile_name]
        cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier']
        aws_cli.run(cmd)

        cmd = ['iam', 'attach-role-policy']
        cmd += ['--role-name', instance_profile_name]
        cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AWSElasticBeanstalkMulticontainerDocker']
        aws_cli.run(cmd)

        cmd = ['iam', 'attach-role-policy']
        cmd += ['--role-name', instance_profile_name]
        cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AWSElasticBeanstalkWorkerTier']
        aws_cli.run(cmd)

        cmd = ['iam', 'attach-role-policy']
        cmd += ['--role-name', instance_profile_name]
        cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore']
        aws_cli.run(cmd)

    print_message(f'create iam role policy: {instance_profile_policy_name}')

    cmd = ['iam', 'put-role-policy']
    cmd += ['--role-name', instance_profile_name]
    cmd += ['--policy-name', instance_profile_policy_name]
    cmd += ['--policy-document', f'file://{dotfile_path}/instance-profile/policy.json']
    aws_cli.run(cmd)
