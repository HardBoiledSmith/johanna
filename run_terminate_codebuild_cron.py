#!/usr/bin/env python3
from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()


def terminate_iam_role_policy(role_name, policy_name):
    print_message('delete iam role policy %s of %s' % (policy_name, role_name))
    cmd = ['iam', 'delete-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-name', policy_name]
    return aws_cli.run(cmd, ignore_error=True)


def terminate_iam_role(role_name):
    print_message('delete iam role %s' % role_name)
    cmd = ['iam', 'delete-role']
    cmd += ['--role-name', role_name]
    return aws_cli.run(cmd, ignore_error=True)


def terminate_iam_for_codebuild():
    role_name = 'aws-codebuild-cron-role'
    policy_name = 'aws-codebuild-cron-policy'
    terminate_iam_role_policy(role_name, policy_name)
    terminate_iam_role(role_name)


def terminate_iam_for_events():
    role_name = 'aws-events-rule-codebuild-role'
    policy_name = 'aws-events-rule-codebuild-policy'
    terminate_iam_role_policy(role_name, policy_name)
    terminate_iam_role(role_name)


def terminate_events():
    for codebuild in env['codebuilds_cron']:
        for cron in codebuild['CRONS']:
            rule_name = '%s_build_%s_cron' % (codebuild['NAME'], cron['BRANCH'])
            print_message('delete events rule %s' % rule_name)
            cmd = ['events', 'remove-targets']
            cmd += ['--rule', rule_name]
            cmd += ['--ids', rule_name]
            aws_cli.run(cmd, ignore_error=True)
            cmd = ['events', 'delete-rule']
            cmd += ['--name', rule_name]
            aws_cli.run(cmd, ignore_error=True)


def terminate_codebuilds():
    for codebuild in env['codebuilds_cron']:
        print_message('delete codebuild %s' % codebuild['NAME'])
        cmd = ['codebuild', 'delete-project']
        cmd += ['--name', codebuild['NAME']]
        aws_cli.run(cmd, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate codebuild')

terminate_codebuilds()
terminate_events()
terminate_iam_for_codebuild()
terminate_iam_for_events()
