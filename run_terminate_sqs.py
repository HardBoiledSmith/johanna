#!/usr/bin/env python3
from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

sqs = env['sqs']
list_region = []
for sqs_env in sqs:
    rr = sqs_env['AWS_DEFAULT_REGION']
    list_region.append(rr)

################################################################################
#
# start
#
################################################################################
print_session('terminate sqs')

################################################################################
for rr in list_region:
    aws_cli = AWSCli(rr)

    print_message('load queue lists')

    cmd = ['sqs', 'list-queues']
    command_result = aws_cli.run(cmd)
    if 'QueueUrls' in command_result:
        sqs = command_result['QueueUrls']

        print_message('delete queues')

        for sqs_env in sqs:
            cmd = ['sqs', 'delete-queue']
            cmd += ['--queue-url', sqs_env]
            aws_cli.run(cmd, ignore_error=True)

            print('delete :', sqs_env)
