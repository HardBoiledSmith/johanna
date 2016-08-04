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
aws_default_region = aws_cli.env['AWS_DEFAULT_REGION']
eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']

################################################################################
#
# start
#
################################################################################
print_session('terminate nova')

################################################################################
print_message('terminate nova')

elapsed_time = 0
while True:
    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--application-name', eb_application_name]
    result = aws_cli.run(cmd)

    count = 0
    for r in result['Environments']:
        if not r['EnvironmentName'].startswith('nova'):
            continue

        if r['Status'] not in ('Ready', 'Terminating', 'Terminated'):
            count += 1
            continue

        if r['Status'] == 'Ready':
            cmd = ['elasticbeanstalk', 'terminate-environment']
            cmd += ['--environment-name', r['EnvironmentName']]
            aws_cli.run(cmd, ignore_error=True)

    if count == 0:
        break

    print 'deleting the environment... (elapsed time: \'%d\' seconds)' % elapsed_time
    time.sleep(5)
    elapsed_time += 5
