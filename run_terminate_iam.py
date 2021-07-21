#!/usr/bin/env python3
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()


def terminate_iam():
    ################################################################################
    #
    # IAM
    #
    ################################################################################
    print_session('terminate iam')

    aws_cli = AWSCli()

    ################################################################################
    print_message('terminate iam: aws-elasticbeanstalk-service-role')

    cmd = ['iam', 'detach-role-policy']
    cmd += ['--role-name', 'aws-elasticbeanstalk-service-role']
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AWSElasticBeanstalkManagedUpdatesCustomerRolePolicy']
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'detach-role-policy']
    cmd += ['--role-name', 'aws-elasticbeanstalk-service-role']
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalkEnhancedHealth']
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'delete-role']
    cmd += ['--role-name', 'aws-elasticbeanstalk-service-role']
    aws_cli.run(cmd, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate iam')

terminate_iam()
