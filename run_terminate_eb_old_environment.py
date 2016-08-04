#!/usr/bin/env python
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

aws_cli = AWSCli()

aws_default_region = env['aws']['AWS_DEFAULT_REGION']
eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']

timestamp = int(time.time())
max_age_seconds = 60 * 50


def _is_old_environment(cname):
    cc = cname.split('.')[0]
    cc = cc.split('-')[-1]

    # noinspection PyBroadException
    try:
        old_timestamp = int(cc)
    except:
        return False

    # 'old_timestamp' MUST NOT be greater than current timestamp
    if old_timestamp > timestamp:
        print 'wrong old timestamp (too big)'
        return False

    # 'old_timestamp' MUST NOT be less than timestamp of '2016-01-01 00:00:00'.
    if old_timestamp < 1451606400:
        print 'wrong old timestamp (too small)'
        return False

    if old_timestamp + max_age_seconds > timestamp:
        print 'skip this time'
        return False

    return True


################################################################################
#
# start
#
################################################################################
print_session('terminate old environment')

################################################################################
print_message('terminate old environment (current timestamp: %d)' % timestamp)

cmd = ['elasticbeanstalk', 'describe-environments']
cmd += ['--application-name', eb_application_name]
result = aws_cli.run(cmd)

for r in result['Environments']:
    # TODO: do we need to handle worker environment(Balthasar) here?
    if 'CNAME' not in r:
        continue

    print ''
    print 'EnvironmentName:', r['EnvironmentName']
    print 'CNAME:', r['CNAME']
    print 'Status:', r['Status']
    print ''

    if r['Status'] != 'Ready':
        continue

    if not _is_old_environment(r['CNAME']):
        continue

    cmd = ['elasticbeanstalk', 'terminate-environment']
    cmd += ['--environment-name', r['EnvironmentName']]
    aws_cli.run(cmd, ignore_error=True)
