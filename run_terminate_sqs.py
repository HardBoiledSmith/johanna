#!/usr/bin/env python3
from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_terminate_queue(name, settings):
    print_message(f'terminate sqs queue: {name}')

    aws_cli = AWSCli(settings['AWS_REGION'])

    cmd = ['sqs', 'get-queue-url']
    cmd += ['--queue-name', f'{name}-dead-letter']
    result = aws_cli.run(cmd, ignore_error=True)

    if result:
        queue_url = result['QueueUrl']
        cmd = ['sqs', 'delete-queue']
        cmd += ['--queue-url', queue_url]
        aws_cli.run(cmd, ignore_error=True)

    cmd = ['sqs', 'get-queue-url']
    cmd += ['--queue-name', name]
    result = aws_cli.run(cmd, ignore_error=True)

    if result:
        queue_url = result['QueueUrl']
        cmd = ['sqs', 'delete-queue']
        cmd += ['--queue-url', queue_url]
        aws_cli.run(cmd, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate sqs')

target_name = None
region = options.get('region')
is_target_exists = False

for settings in env.get('sqs', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True

    run_terminate_queue(settings['NAME'], settings)

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'sqs: {mm} is not found in config.json')
