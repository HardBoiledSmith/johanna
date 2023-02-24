#!/usr/bin/env python3
import json
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_create_standard_queue(name, settings):
    print_message(f'create sqs queue: {name}')

    delay_seconds = settings['DELAY_SECONDS']
    receive_count = settings['RECEIVE_COUNT']
    receive_message_wait_time_seconds = settings['RECEIVE_MESSAGE_WAIT_TIME_SECONDS']
    retention = settings['RETENTION']
    timeout = settings['TIMEOUT']
    use_redrive_policy = settings['USE_REDRIVE_POLICY']
    dead_letter_queue_arn = None

    aws_cli = AWSCli(settings['AWS_REGION'])

    if use_redrive_policy == "True":
        attributes = dict()
        attributes['MessageRetentionPeriod'] = retention

        cmd = ['sqs', 'create-queue']
        cmd += ['--queue-name', f'{name}-dead-letter']
        cmd += ['--attributes', json.dumps(attributes)]
        aws_cli.run(cmd)

        elapsed_time = 0
        while elapsed_time < 120:
            cmd = ['sqs', 'get-queue-url', '--queue-name', f'{name}-dead-letter']
            result = aws_cli.run(cmd)

            if type(result) == dict:
                if result.get('QueueUrl', None):
                    break

            print('get url... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

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
    aws_cli.run(cmd)


def run_create_fifo_queue(name, settings):
    print_message(f'create sqs queue: {name}')

    delay_seconds = settings['DELAY_SECONDS']
    receive_count = settings['RECEIVE_COUNT']
    receive_message_wait_time_seconds = settings['RECEIVE_MESSAGE_WAIT_TIME_SECONDS']
    retention = settings['RETENTION']
    timeout = settings['TIMEOUT']
    use_redrive_policy = settings['USE_REDRIVE_POLICY']
    dead_letter_queue_arn = None

    aws_cli = AWSCli(settings['AWS_REGION'])

    if use_redrive_policy == "True":
        attributes = dict()
        attributes['MessageRetentionPeriod'] = retention
        attributes['FifoQueue'] = "true"
        attributes['ContentBasedDeduplication'] = "true"

        queue_name = name.replace('.fifo', '')

        cmd = ['sqs', 'create-queue']
        cmd += ['--queue-name', f'{queue_name}-dead-letter.fifo']
        cmd += ['--attributes', json.dumps(attributes)]
        aws_cli.run(cmd)

        elapsed_time = 0
        while elapsed_time < 120:
            cmd = ['sqs', 'get-queue-url', '--queue-name', f'{queue_name}-dead-letter.fifo']
            result = aws_cli.run(cmd)

            if type(result) == dict and result.get('QueueUrl', None):
                    break

            print('get url... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

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
    attr['FifoQueue'] = "true"
    attr['ContentBasedDeduplication'] = "true"

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

target_name = None
region = options.get('region')
is_target_exists = False

for settings in env.get('sqs', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True

    if settings['SQS_TYPE'] == 'STANDARD':
        run_create_standard_queue(settings['NAME'], settings)
    elif settings['SQS_TYPE'] == 'FIFO':
        run_create_fifo_queue(settings['NAME'], settings)
    else:
        print('The SQS TYPE variable has no value.')
        raise Exception()

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'sqs: {mm} is not found in config.json')
