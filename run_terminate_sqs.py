#!/usr/bin/env python3
from __future__ import print_function

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

aws_cli = AWSCli()

################################################################################
#
# start
#
################################################################################
print_session('terminate sqs')

################################################################################
print_message('load queue lists')

cmd = ['sqs', 'list-queues']
command_result = aws_cli.run(cmd)
queues = command_result['QueueUrls']

################################################################################
print_message('delete queues')

for queue in queues:
    cmd = ['sqs', 'delete-queue']
    cmd += ['--queue-url', queue]
    aws_cli.run(cmd)

    print('delete : ' + queue)
