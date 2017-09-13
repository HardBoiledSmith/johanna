#!/usr/bin/env python3
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()
aws_default_region = aws_cli.env['AWS_DEFAULT_REGION']
eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']


def run_terminate_environment(name):
    print_message('terminate %s' % name)

    elapsed_time = 0
    while True:
        cmd = ['elasticbeanstalk', 'describe-environments']
        cmd += ['--application-name', eb_application_name]
        result = aws_cli.run(cmd)

        count = 0
        for r in result['Environments']:
            if not r['EnvironmentName'].startswith(name):
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

        print('deleting the environment... (elapsed time: \'%d\' seconds)' % elapsed_time)
        time.sleep(5)
        elapsed_time += 5


################################################################################
#
# start
#
################################################################################
print_session('terminate eb')

eb = env['elasticbeanstalk']
if len(args) == 2:
    target_eb_name = args[1]
    target_eb_name_exists = False
    for eb_env in eb['ENVIRONMENTS']:
        if eb_env['NAME'] == target_eb_name:
            target_eb_name_exists = True
            run_terminate_environment(eb_env['NAME'])
            break
    if not target_eb_name_exists:
        print('"%s" is not exists in config.json' % target_eb_name)
else:
    for eb_env in eb['ENVIRONMENTS']:
        run_terminate_environment(eb_env['NAME'])
