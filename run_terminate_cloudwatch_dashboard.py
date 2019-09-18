#!/usr/bin/env python3

import json

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def run_terminate_cw_dashboard(name, settings):
    region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(region)

    dashboard_name = '%s_%s' % (name, region)
    print_message('terminate cloudwatch dashboard: %s' % dashboard_name)

    cmd = ['cloudwatch', 'delete-dashboards']
    cmd += ['--dashboard-names', dashboard_name]
    aws_cli.run(cmd)


def delete_role_for_sms():
    aws_cli = AWSCli('ap-northeast-1')

    role_name = 'aws-sns-sms-log-role'
    policy_name = 'aws-sns-sms-log-policy'

    cmd = ['iam', 'delete-role-policy']
    cmd += ['--role-name', role_name]
    cmd += ['--policy-nam', policy_name]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'delete-role']
    cmd += ['--role-name', role_name]
    aws_cli.run(cmd, ignore_error=True)

    print_message('stop sms log')

    dd = {'attributes': {'DeliveryStatusSuccessSamplingRate': '',
                         'DeliveryStatusIAMRole': ''}}
    cmd = ['sns', 'set-sms-attributes']
    cmd += ['--cli-input-json', json.dumps(dd)]
    aws_cli.run(cmd, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate cloudwatch dashboard')

cw = env.get('cloudwatch', dict())

if len(args) == 2:
    target_cw_dashboard_name = args[1]
    target_cw_dashboard_name_exists = False

    for cw_dashboard_env in cw.get('DASHBOARDS', list()):
        if cw_dashboard_env['NAME'] == target_cw_dashboard_name:
            target_cw_dashboard_name_exists = True
            run_terminate_cw_dashboard(cw_dashboard_env['NAME'], cw_dashboard_env)
    if not target_cw_dashboard_name_exists:
        print('"%s" is not exists in config.json' % target_cw_dashboard_name)
else:
    for cw_dashboard_env in cw.get('DASHBOARDS', list()):
        run_terminate_cw_dashboard(cw_dashboard_env['NAME'], cw_dashboard_env)

delete_role_for_sms()
