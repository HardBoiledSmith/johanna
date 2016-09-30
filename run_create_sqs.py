#!/usr/bin/env python3
from __future__ import print_function

import json

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
print_session('create sqs')

################################################################################
print_message('create queue')

attr = dict()
attr['VisibilityTimeout'] = "30"
attr['MessageRetentionPeriod'] = "345600"
attr['DelaySeconds'] = "0"
attr['ReceiveMessageWaitTimeSeconds'] = "0"

cmd = ['sqs', 'create-queue']
cmd += ['--queue-name', 'sqs-test']
cmd += ['--attributes', json.dumps(attr)]
aws_cli.run(cmd)
