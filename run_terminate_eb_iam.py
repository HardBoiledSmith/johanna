from run_common import AWSCli


def terminate_iam_profile_for_ec2_instances(name):
    aws_cli = AWSCli()

    policy_name = f'aws-elasticbeanstalk-{name}-ec2-policy'
    role_name = f'aws-elasticbeanstalk-{name}-ec2-role'

    cmd = ['iam', 'delete-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-name', policy_name]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'detach-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AWSElasticBeanstalkWorkerTier']
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'detach-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AWSElasticBeanstalkMulticontainerDocker']
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'detach-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier']
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'detach-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore']
    aws_cli.run(cmd, ignore_error=True)

    profile_name = f'aws-elasticbeanstalk-{name}-instance-profile'

    cmd = ['iam', 'remove-role-from-instance-profile']
    cmd += ['--instance-profile-name', profile_name]
    cmd += ['--role-name', role_name]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'delete-role']
    cmd += ['--role-name', role_name]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'delete-instance-profile']
    cmd += ['--instance-profile-name', profile_name]
    aws_cli.run(cmd, ignore_error=True)
