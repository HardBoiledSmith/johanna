#!/usr/bin/env python3
import json
import time

from env import env
from run_common import check_template_availability
from run_common import print_message
from run_common import print_session
from run_common import AWSCli

args = []
sleep_interval = 120

if __name__ == '__main__':
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()


def create_iam_role(role_name, role_file_path):
    if not aws_cli.get_iam_role(role_name) and role_file_path:
        print_message('create iam role %s' % role_name)

        cmd = ['iam', 'create-role']
        cmd += ['--role-name', role_name]
        cmd += ['--assume-role-policy-document', role_file_path]
        return aws_cli.run(cmd)


def create_iam_role_policy(role_name, policy_name, policy_file_path):
    if not aws_cli.get_iam_role_policy(role_name, policy_name) and policy_file_path:
        print_message('create iam role policy %s of %s' % (policy_name, role_name))

        cmd = ['iam', 'put-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-name', policy_name]
        cmd += ['--policy-document', policy_file_path]
        return aws_cli.run(cmd)


def create_iam_for_codebuild():
    print_message('start create iam role for codebuild')
    role_name = 'aws-codebuild-cron-role'
    policy_name = 'aws-codebuild-cron-policy'

    role = create_iam_role(role_name,
                           role_file_path='file://aws_iam/aws-codebuild-cron-role.json')
    if not role or not role['Role'] or not role['Role']['Arn']:
        raise Exception('fail to create iam role')

    create_iam_role_policy(role_name,
                           policy_name,
                           policy_file_path='file://aws_iam/aws-codebuild-cron-policy.json')

    print_message('end create iam role for codebuild')
    print_message('wait two minutes to let iam role and policy propagated to all regions...')
    time.sleep(sleep_interval)

    return role['Role']


def create_iam_for_cron_rule():
    print_message('start create iam role for cron rule of codebuild')
    role_name = 'aws-events-rule-codebuild-role'
    policy_name = 'aws-events-rule-codebuild-policy'

    role = create_iam_role(role_name,
                           role_file_path='file://aws_iam/aws-events-rule-codebuild-role.json')
    if not role or not role['Role'] or not role['Role']['Arn']:
        raise Exception('fail to create iam role')

    create_iam_role_policy(role_name,
                           policy_name,
                           policy_file_path='file://aws_iam/aws-events-rule-codebuild-policy.json')

    print_message('end create iam role for codebuild')
    print_message('wait two minutes to let iam role and policy propagated to all regions...')
    time.sleep(sleep_interval)

    return role['Role']


################################################################################
#
# start
#
################################################################################
print_session('create codebuild')


def create_events_rule(codebuild_name, codebuild_arn, role_arn, crons):
    for cron in crons:
        rule_name = '%s_build_%s_cron' % (codebuild_name, cron['BRANCH'])
        cmd = ['events', 'put-rule']
        cmd += ['--name', rule_name]
        cmd += ['--schedule-expression', cron['SCHEDULE_EXPRESSION']]
        rule = aws_cli.run(cmd)
        if not rule or not rule['RuleArn']:
            raise Exception('fail create events rule %s' % rule_name)
        cmd = ['events', 'put-targets']
        cmd += ['--rule', rule_name]
        cmd += ['--targets', json.dumps([
            {
                "Id": rule_name,
                "Arn": codebuild_arn,
                "RoleArn": role_arn,
                "Input": json.dumps({"sourceVersion": cron['BRANCH'], "timeoutInMinutesOverride": 60})
            }
        ])]
        target = aws_cli.run(cmd)
        print(target)


check_template_availability()


def create_codebuild_cron():
    cron_role = create_iam_for_cron_rule()
    codebuild_role = create_iam_for_codebuild()
    for codebuild in env['codebuilds_cron']:
        cmd = ['codebuild', 'create-project', '--cli-input-json', json.dumps({
            "name": codebuild['NAME'],
            "description": "for %s" % codebuild['NAME'],
            "source": {
                "type": "GITHUB_ENTERPRISE",
                "location": codebuild['GITHUB_REPO'],
                "gitCloneDepth": 0,
                "buildspec": codebuild['BUILD_SPEC'],
                "auth": {
                    "type": "OAUTH",
                    "resource": codebuild['GITHUB_TOKEN']
                },
                "insecureSsl": True
            },
            "artifacts": {
                "type": "NO_ARTIFACTS"
            },
            "cache": {
                "type": "NO_CACHE"
            },
            "environment": {
                "type": "LINUX_CONTAINER",
                "image": "aws/codebuild/eb-python-3.4-amazonlinux-64:2.1.6",
                "computeType": codebuild['ENV_COMPUTE_TYPE'],
                "environmentVariables": codebuild['ENV_VARIABLES']
            },
            "serviceRole": codebuild_role['Arn'],
            "timeoutInMinutes": codebuild['BUILD_TIMEOUT'],
            "badgeEnabled": True
        }
        )]
        result = aws_cli.run(cmd)
        if not result or not result['project'] or not result['project']['arn']:
            raise Exception('fail to create codebuild %s' % codebuild['NAME'])
        create_events_rule(codebuild['NAME'], result['project']['arn'], cron_role['Arn'], codebuild['CRONS'])


create_codebuild_cron()
