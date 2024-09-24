#!/usr/bin/env python3.12
import json

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_terminate_lambda_iam import terminate_iam_for_lambda

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_terminate_default_lambda(function_name, settings):
    aws_cli = AWSCli(settings['AWS_REGION'])

    ################################################################################
    print_session(f'terminate lambda: {function_name}')

    print_message('delete lambda function')

    cmd = ['lambda', 'delete-function',
           '--function-name', function_name]
    aws_cli.run(cmd, ignore_error=True)


def run_terminate_cron_lambda(function_name, settings):
    aws_cli = AWSCli(settings['AWS_REGION'])

    ################################################################################
    print_session(f'terminate lambda: {function_name}')

    print_message('unlink event and lambda')

    cmd = ['events', 'list-targets-by-rule',
           '--rule', function_name + 'CronRule']
    result = aws_cli.run(cmd, ignore_error=True)
    if type(result) is dict:
        target_list = result['Targets']
    else:
        target_list = list()

    ids_list = []
    for target in target_list:
        target_id = f"\"{target['Id']}\""
        ids_list.append(target_id)
    ids_list = f"[{','.join(ids_list)}]"

    cmd = ['events', 'remove-targets',
           '--rule', function_name + 'CronRule',
           '--ids', ids_list]
    aws_cli.run(cmd, ignore_error=True)

    print_message('remove event permission')

    cmd = ['lambda', 'remove-permission',
           '--function-name', function_name,
           '--statement-id', function_name + 'StatementId']
    aws_cli.run(cmd, ignore_error=True)

    print_message('delete cron event')

    cmd = ['events', 'delete-rule',
           '--name', function_name + 'CronRule']
    aws_cli.run(cmd, ignore_error=True)

    print_message('delete lambda function')

    cmd = ['lambda', 'delete-function',
           '--function-name', function_name]
    aws_cli.run(cmd, ignore_error=True)


def run_terminate_sns_lambda(function_name, settings):
    aws_cli = AWSCli(settings['AWS_REGION'])

    ################################################################################
    print_session(f'terminate lambda: {function_name}')

    cmd = ['lambda', 'get-policy',
           '--function-name', function_name]
    result = aws_cli.run(cmd, ignore_error=True)

    if result:
        policy = result['Policy']
        policy = json.loads(policy)

        statement_list = policy['Statement']

        for statement in statement_list:
            print_message('remove subscription')

            arn_like = statement['Condition']['ArnLike']
            source_arn = arn_like['AWS:SourceArn']

            sns_region = source_arn.split(':')[3]

            cmd = ['sns', 'list-subscriptions-by-topic',
                   '--topic-arn', source_arn]
            result = AWSCli(sns_region).run(cmd, ignore_error=True)
            if not result:
                continue

            subscription_list = result['Subscriptions']
            for subscription in subscription_list:
                if subscription['Protocol'] != 'lambda':
                    continue

                subscription_arn = subscription['SubscriptionArn']
                cmd = ['sns', 'unsubscribe',
                       '--subscription-arn', subscription_arn]
                AWSCli(sns_region).run(cmd, ignore_error=True)

    print_message('delete lambda function')

    cmd = ['lambda', 'delete-function',
           '--function-name', function_name]
    aws_cli.run(cmd, ignore_error=True)


def run_terminate_sqs_lambda(function_name, settings):
    aws_cli = AWSCli(settings['AWS_REGION'])

    ################################################################################
    print_session(f'terminate lambda: {function_name}')

    print_message(f'delete event sources for {function_name}')
    cmd = ['lambda', 'list-event-source-mappings',
           '--function-name', function_name]
    mappings = aws_cli.run(cmd)['EventSourceMappings']
    for mapping in mappings:
        cmd = ['lambda', 'delete-event-source-mapping',
               '--uuid', mapping['UUID']]
        aws_cli.run(cmd)

    print_message('delete lambda function')
    cmd = ['lambda', 'delete-function',
           '--function-name', function_name]
    aws_cli.run(cmd, ignore_error=True)


def run_terminate_ses_sqs_lambda(function_name, settings):
    aws_cli = AWSCli(settings['AWS_REGION'])

    ################################################################################
    print_session(f'terminate lambda: {function_name}')

    print_message(f'delete event sources for {function_name}')
    cmd = ['lambda', 'list-event-source-mappings',
           '--function-name', function_name]
    mappings = aws_cli.run(cmd)['EventSourceMappings']
    for mapping in mappings:
        cmd = ['lambda', 'delete-event-source-mapping',
               '--uuid', mapping['UUID']]
        aws_cli.run(cmd)

    print_message('delete lambda function')
    cmd = ['lambda', 'delete-function',
           '--function-name', function_name]
    aws_cli.run(cmd, ignore_error=True)


def run_terminate_event_lambda(function_name, settings):
    aws_cli = AWSCli(settings['AWS_REGION'])

    ################################################################################
    print_session(f'terminate lambda: {function_name}')

    print_message('unlink event and lambda')

    cmd = ['events', 'remove-targets',
           '--rule', settings['EVENT_NAME'],
           '--ids', settings['EVENT_NAME']]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['events', 'delete-rule',
           '--name', settings['EVENT_NAME']]
    aws_cli.run(cmd, ignore_error=True)

    print_message('delete lambda function')

    cmd = ['lambda', 'delete-function',
           '--function-name', function_name]
    aws_cli.run(cmd, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate lambda')

target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in env.get('lambda', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True

    if settings['TYPE'] == 'default':
        run_terminate_default_lambda(settings['NAME'], settings)
        terminate_iam_for_lambda(settings['NAME'])
    elif settings['TYPE'] == 'cron':
        run_terminate_cron_lambda(settings['NAME'], settings)
        terminate_iam_for_lambda(settings['NAME'])
    elif settings['TYPE'] == 'sns':
        run_terminate_sns_lambda(settings['NAME'], settings)
        terminate_iam_for_lambda(settings['NAME'])
    elif settings['TYPE'] == 'sqs':
        run_terminate_sqs_lambda(settings['NAME'], settings)
        terminate_iam_for_lambda(settings['NAME'])
    elif settings['TYPE'] == 'ses_sqs':
        run_terminate_ses_sqs_lambda(settings['NAME'], settings)
        terminate_iam_for_lambda(settings['NAME'])
    elif settings['TYPE'] == 'event':
        run_terminate_event_lambda(settings['NAME'], settings)
        terminate_iam_for_lambda(settings['NAME'])
    else:
        print(f'{settings["TYPE"]} is not supported')
        raise Exception()

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'lambda: {mm} is not found in config.json')
