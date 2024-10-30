#!/usr/bin/env python3

import time
import subprocess

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()


def _is_old_environment(cname):
    cc = cname.split('.')[0]
    cc = cc.split('-')[-1]

    # noinspection PyBroadException
    try:
        old_timestamp = int(cc)
    except Exception:
        return False

    # 'old_timestamp' MUST NOT be greater than current timestamp
    if old_timestamp > timestamp:
        print('wrong old timestamp (too big)')
        return False

    # 'old_timestamp' MUST NOT be less than timestamp of '2016-01-01 00:00:00'.
    if old_timestamp < 1451606400:
        print('wrong old timestamp (too small)')
        return False

    if old_timestamp + max_age_seconds > timestamp:
        print('skip this time')
        return False

    return True


def _has_no_instances(env_name):
    cmd = ['ec2', 'describe-instances']
    cmd += ['--filters', f"Name=tag:Name,Values={env_name}"]
    cmd += ['Name=instance-state-name,Values=running']
    cmd += ['--query', 'Reservations[*].Instances[*].InstanceId']
    cmd += ['--output', 'text']

    result = aws_cli.run(cmd)
    count = subprocess.run(['wc', '-l'], input=result, text=True, capture_output=True)

    return int(count.stdout.strip()) == 0


################################################################################
#
# start
#
################################################################################
print_session('terminate old environment')

timestamp = int(time.time())
max_age_seconds = 60 * 50

################################################################################
print_message('terminate old environment (current timestamp: %d)' % timestamp)

eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']

for vpc_env in env.get('vpc', list()):
    aws_cli = AWSCli(vpc_env['AWS_REGION'])
    aws_region = vpc_env['AWS_REGION']

    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--application-name', eb_application_name]
    result = aws_cli.run(cmd)

    for r in result['Environments']:
        if 'CNAME' not in r:
            continue

        print('')
        print('EnvironmentName:', r['EnvironmentName'])
        print('CNAME:', r['CNAME'])
        print('Status:', r['Status'])
        print('')

        if r['Status'] != 'Ready':
            continue

        if not _is_old_environment(r['CNAME']):
            continue

        if 'kaji' in r['CNAME'] and not _has_no_instances(r['EnvironmentName']):
            continue

        if 'gendo' in r['CNAME'] and not _has_no_instances(r['EnvironmentName']):
            continue

        cmd = ['cloudwatch', 'delete-alarms']
        cmd += ['--alarm-names', f'{r["EnvironmentName"]}_nginx_error_log']
        aws_cli.run(cmd, ignore_error=True)

        cmd = ['cloudwatch', 'delete-alarms']
        cmd += ['--alarm-names', f'{r["EnvironmentName"]}_httpd_error_log']
        aws_cli.run(cmd, ignore_error=True)

        cmd = ['elasticbeanstalk', 'terminate-environment']
        cmd += ['--environment-name', r['EnvironmentName']]
        aws_cli.run(cmd, ignore_error=True)
