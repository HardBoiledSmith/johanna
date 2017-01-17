#!/usr/bin/env python3
from __future__ import print_function

import json

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()


def run_create_queue(name, settings):
    print_message('create ' + name)

    attr = dict()
    attr['VisibilityTimeout'] = settings['TIMEOUT']
    attr['MessageRetentionPeriod'] = settings['RETENTION']
    attr['DelaySeconds'] = settings['DELAY_SECONDS']
    attr['ReceiveMessageWaitTimeSeconds'] = settings['RECEIVE_COUNT']

    cmd = ['sqs', 'create-queue']
    cmd += ['--queue-name', name]
    cmd += ['--attributes', json.dumps(attr)]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('create sqs')

################################################################################

queue_list = env['sqs']
if len(args) == 2:
    target_eb_name = args[1]
    for queue in queue_list:
        if queue['NAME'] == target_eb_name:
            run_create_queue(queue['NAME'], queue)
            break
    print('"%s" is not exists in config.json' % target_eb_name)
else:
    for queue in queue_list:
        run_create_queue(queue['NAME'], queue)
