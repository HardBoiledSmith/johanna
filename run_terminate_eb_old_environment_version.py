#!/usr/bin/env python3
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()


def _is_old_environment(version_label):
    cc = version_label.split('-')[-1]

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


################################################################################
#
# start
#
################################################################################
print_session('terminate old environment version')

timestamp = int(time.time())
max_age_seconds = 60 * 60 * 24 * 3

################################################################################
print_message('terminate old environment version (current timestamp: %d)' % timestamp)

eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']

for vpc_env in env['vpc']:
    aws_cli = AWSCli(vpc_env['AWS_DEFAULT_REGION'])
    aws_default_region = vpc_env['AWS_DEFAULT_REGION']

    cmd = ['elasticbeanstalk', 'describe-application-versions']
    cmd += ['--application-name', eb_application_name]
    result = aws_cli.run(cmd)

    for r in result['ApplicationVersions']:
        if r['Status'] in ('PROCESSING', 'BUILDING'):
            continue

        print('')
        print('ApplicationName:', r['ApplicationName'])
        print('VersionLabel:', r['VersionLabel'])
        print('Status:', r['Status'])
        print('')

        if not _is_old_environment(r['VersionLabel']):
            continue

        cmd = ['elasticbeanstalk', 'delete-application-version']
        cmd += ['--application-name', eb_application_name]
        cmd += ['--version-label', r['VersionLabel']]
        cmd += ['--delete-source-bundle']
        aws_cli.run(cmd, ignore_error=True)
