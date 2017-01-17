#!/usr/bin/env python3
from __future__ import print_function

import json

from env import env
from run_common import AWSCli
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

aws_cli = AWSCli()


def run_create_queue(name, settings):
    attr = dict()
    attr['VisibilityTimeout'] = settings['TIMEOUT']
    attr['MessageRetentionPeriod'] = settings['RETENTION']
    attr['DelaySeconds'] = settings['DELAY_SECONDS']
    attr['ReceiveMessageWaitTimeSeconds'] = settings['RECEIVE_COUNT']

    cmd = ['sqs', 'create-queue']
    cmd += ['--queue-name', name]
    cmd += ['--attributes', json.dumps(attr)]
    aws_cli.run(cmd)

    print('create : ' + queue)


################################################################################
#
# start
#
################################################################################
print_session('create sqs')

################################################################################
queues = env['sqs']
for queue in queues:
    run_create_queue(queue['NAME'], queue)
