#!/usr/bin/env python3.11
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_terminate_eb_iam import terminate_iam_profile_for_ec2_instances

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_terminate_environment(name, settings):
    aws_cli = AWSCli(settings['AWS_REGION'])
    eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']

    print_message(f'terminate {name}')

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

                cmd = ['cloudwatch', 'delete-alarms']
                cmd += ['--alarm-names', f'{r["EnvironmentName"]}_nginx_error_log']
                aws_cli.run(cmd, ignore_error=True)

                cmd = ['cloudwatch', 'delete-alarms']
                cmd += ['--alarm-names', f'{r["EnvironmentName"]}_httpd_error_log']
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
target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in eb.get('ENVIRONMENTS', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True

    run_terminate_environment(settings['NAME'], settings)
    terminate_iam_profile_for_ec2_instances(settings['NAME'])

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'eb environment: {mm} is not found in config.json')
