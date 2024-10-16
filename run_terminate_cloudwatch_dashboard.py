#!/usr/bin/env python3.12

import json

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_terminate_cw_dashboard(name, settings):
    region = settings['AWS_REGION']
    aws_cli = AWSCli(region)

    dashboard_name = f'{name}_{region}'
    print_message(f'terminate cloudwatch dashboard: {dashboard_name}')

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
target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in cw.get('DASHBOARDS', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True

    run_terminate_cw_dashboard(settings['NAME'], settings)

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'cloudwatch dashboard: {mm} is not found in config.json')

if not target_name and not region:
    delete_role_for_sms()
