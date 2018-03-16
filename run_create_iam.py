#!/usr/bin/env python3

from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()


def create_iam():
    ################################################################################
    #
    # IAM
    #
    ################################################################################
    print_session('create iam')

    aws_cli = AWSCli()

    ################################################################################
    print_message('create iam: aws-elasticbeanstalk-ec2-role')

    cmd = ['iam', 'create-instance-profile']
    cmd += ['--instance-profile-name', 'aws-elasticbeanstalk-ec2-role']
    aws_cli.run(cmd)

    cmd = ['iam', 'create-role']
    cmd += ['--role-name', 'aws-elasticbeanstalk-ec2-role']
    cmd += ['--assume-role-policy-document', 'file://aws_iam/aws-elasticbeanstalk-ec2-role.json']
    aws_cli.run(cmd)

    cmd = ['iam', 'add-role-to-instance-profile']
    cmd += ['--instance-profile-name', 'aws-elasticbeanstalk-ec2-role']
    cmd += ['--role-name', 'aws-elasticbeanstalk-ec2-role']
    aws_cli.run(cmd)

    cmd = ['iam', 'attach-role-policy']
    cmd += ['--role-name', 'aws-elasticbeanstalk-ec2-role']
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier']
    aws_cli.run(cmd)

    cmd = ['iam', 'attach-role-policy']
    cmd += ['--role-name', 'aws-elasticbeanstalk-ec2-role']
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AWSElasticBeanstalkMulticontainerDocker']
    aws_cli.run(cmd)

    cmd = ['iam', 'attach-role-policy']
    cmd += ['--role-name', 'aws-elasticbeanstalk-ec2-role']
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AWSElasticBeanstalkWorkerTier']
    aws_cli.run(cmd)

    ################################################################################
    print_message('create iam: aws-elasticbeanstalk-service-role')

    cmd = ['iam', 'create-role']
    cmd += ['--role-name', 'aws-elasticbeanstalk-service-role']
    cmd += ['--assume-role-policy-document', 'file://aws_iam/aws-elasticbeanstalk-service-role.json']
    aws_cli.run(cmd)

    cmd = ['iam', 'attach-role-policy']
    cmd += ['--role-name', 'aws-elasticbeanstalk-service-role']
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalkEnhancedHealth']
    aws_cli.run(cmd)

    cmd = ['iam', 'attach-role-policy']
    cmd += ['--role-name', 'aws-elasticbeanstalk-service-role']
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalkService']
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('create iam')

create_iam()
