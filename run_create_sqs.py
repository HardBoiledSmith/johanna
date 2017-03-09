#!/usr/bin/env python3
from __future__ import print_function

import json
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

aws_cli = AWSCli()


def run_create_queue(name, settings):
    delay_seconds = settings['DELAY_SECONDS']
    receive_count = settings['RECEIVE_COUNT']
    receive_message_wait_time_seconds = settings['RECEIVE_MESSAGE_WAIT_TIME_SECONDS']
    retention = settings['RETENTION']
    timeout = settings['TIMEOUT']
    use_redrive_policy = settings['USE_REDRIVE_POLICY']
    dead_letter_queue_arn = None

    if use_redrive_policy == "True":
        ################################################################################
        print_message('create queue (dead letter)')

        attributes = dict()
        attributes['MessageRetentionPeriod'] = retention

        cmd = ['sqs', 'create-queue']
        cmd += ['--queue-name', '%s-dead-letter' % name]
        cmd += ['--attributes', json.dumps(attributes)]
        result = aws_cli.run(cmd)

        print('create :', result['QueueUrl'])

        ################################################################################
        print_message('get queue url (dead letter)')

        elapsed_time = 0
        while True:
            cmd = ['sqs', 'get-queue-url', '--queue-name', '%s-dead-letter' % name]
            result = aws_cli.run(cmd)

            if type(result) == dict:
                if result.get('QueueUrl', None):
                    break

            print('get url... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

        ################################################################################
        print_message('get queue arn (dead letter)')

        cmd = ['sqs', 'get-queue-attributes']
        cmd += ['--queue-url', result['QueueUrl']]
        cmd += ['--attribute-names', 'QueueArn']
        result = aws_cli.run(cmd)
        dead_letter_queue_arn = result['Attributes']['QueueArn']

    redrive_policy = dict()
    redrive_policy['deadLetterTargetArn'] = dead_letter_queue_arn
    redrive_policy['maxReceiveCount'] = receive_count

    attr = dict()
    if dead_letter_queue_arn is not None:
        attr['RedrivePolicy'] = json.dumps(redrive_policy)
    attr['DelaySeconds'] = delay_seconds
    attr['MessageRetentionPeriod'] = retention
    attr['ReceiveMessageWaitTimeSeconds'] = receive_message_wait_time_seconds
    attr['VisibilityTimeout'] = timeout

    cmd = ['sqs', 'create-queue']
    cmd += ['--queue-name', name]
    cmd += ['--attributes', json.dumps(attr)]
    result = aws_cli.run(cmd)

    print('create :', result['QueueUrl'])


################################################################################
#
# start
#
################################################################################
print_session('create sqs')

################################################################################
sqs = env['sqs']
for sqs_env in sqs:
    run_create_queue(sqs_env['NAME'], sqs_env)
