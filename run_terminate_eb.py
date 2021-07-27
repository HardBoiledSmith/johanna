#!/usr/bin/env python3
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_terminate_eb_iam import terminate_iam_profile_for_ec2_instances

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def run_terminate_environment(name):
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

eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']

for vpc_env in env['vpc']:
    aws_cli = AWSCli(vpc_env['AWS_DEFAULT_REGION'])
    aws_default_region = vpc_env['AWS_DEFAULT_REGION']

    eb = env['elasticbeanstalk']

    if len(args) == 2:
        target_eb_name = args[1]
        target_eb_name_exists = False
        for eb_env in eb['ENVIRONMENTS']:
            if eb_env['NAME'] == target_eb_name:
                target_eb_name_exists = True
                run_terminate_environment(eb_env['NAME'])
                terminate_iam_profile_for_ec2_instances(eb_env['NAME'])
                break
        if not target_eb_name_exists:
            print(f'"{target_eb_name}" is not exists in config.json')
    else:
        for eb_env in eb['ENVIRONMENTS']:
            run_terminate_environment(eb_env['NAME'])
            terminate_iam_profile_for_ec2_instances(eb_env['NAME'])
