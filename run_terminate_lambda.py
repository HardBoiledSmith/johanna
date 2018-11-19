#!/usr/bin/env python3
import json

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def terminate_iam_for_lambda(lambda_type):
    aws_cli = AWSCli()

    print_message('delete iam role policy')

    cmd = ['iam', 'delete-role-policy']
    cmd += ['--role-name', 'aws-lambda-%s-role' % lambda_type]
    cmd += ['--policy-name', 'aws-lambda-%s-policy' % lambda_type]
    aws_cli.run(cmd, ignore_error=True)

    print_message('delete iam role')

    cmd = ['iam', 'delete-role']
    cmd += ['--role-name', 'aws-lambda-%s-role' % lambda_type]
    aws_cli.run(cmd, ignore_error=True)


def run_terminate_default_lambda(function_name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    folder_name = settings.get('FOLDER_NAME', function_name)
    template_name = env['template']['NAME']

    template_path = 'template/%s' % template_name
    deploy_folder = '%s/lambda/%s' % (template_path, folder_name)

    ################################################################################
    print_session('terminate lambda: %s' % function_name)

    print_message('delete lambda function')

    cmd = ['lambda', 'delete-function',
           '--function-name', function_name]
    aws_cli.run(cmd, cwd=deploy_folder, ignore_error=True)


def run_terminate_cron_lambda(function_name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    folder_name = settings.get('FOLDER_NAME', function_name)
    template_name = env['template']['NAME']

    template_path = 'template/%s' % template_name
    deploy_folder = '%s/lambda/%s' % (template_path, folder_name)

    ################################################################################
    print_session('terminate lambda: %s' % function_name)

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
        target_id = '"%s"' % target['Id']
        ids_list.append(target_id)
    ids_list = '[%s]' % ','.join(ids_list)

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
    aws_cli.run(cmd, cwd=deploy_folder, ignore_error=True)


def run_terminate_sns_lambda(function_name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    folder_name = settings.get('FOLDER_NAME', function_name)
    template_name = env['template']['NAME']

    template_path = 'template/%s' % template_name
    deploy_folder = '%s/lambda/%s' % (template_path, folder_name)

    ################################################################################
    print_session('terminate lambda: %s' % function_name)

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
    aws_cli.run(cmd, cwd=deploy_folder, ignore_error=True)


def run_terminate_sqs_lambda(function_name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    folder_name = settings.get('FOLDER_NAME', function_name)
    template_name = env['template']['NAME']

    template_path = 'template/%s' % template_name
    deploy_folder = '%s/lambda/%s' % (template_path, folder_name)

    ################################################################################
    print_session('terminate lambda: %s' % function_name)

    print_message('delete event sources for %s' % function_name)
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
    aws_cli.run(cmd, cwd=deploy_folder, ignore_error=True)


def run_terminate_event_lambda(function_name, settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])

    folder_name = settings.get('FOLDER_NAME', function_name)
    template_name = env['template']['NAME']

    template_path = 'template/%s' % template_name
    deploy_folder = '%s/lambda/%s' % (template_path, folder_name)

    ################################################################################
    print_session('terminate lambda: %s' % function_name)

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
    aws_cli.run(cmd, cwd=deploy_folder, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate lambda')

lambdas_list = env.get('lambda', list())
if len(args) == 2:
    target_lambda_name = args[1]
    target_lambda_name_exists = False
    for lambda_env in lambdas_list:
        if lambda_env['NAME'] == target_lambda_name:
            target_lambda_name_exists = True
            if lambda_env['TYPE'] == 'default':
                run_terminate_default_lambda(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'cron':
                run_terminate_cron_lambda(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'sns':
                run_terminate_sns_lambda(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'sqs':
                run_terminate_sqs_lambda(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'event':
                run_terminate_event_lambda(lambda_env['NAME'], lambda_env)
                continue
            print('"%s" is not supported' % lambda_env['TYPE'])
            raise Exception()
    if not target_lambda_name_exists:
        print('"%s" is not exists in config.json' % target_lambda_name)
else:
    for lambda_env in lambdas_list:
        if lambda_env['TYPE'] == 'default':
            run_terminate_default_lambda(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'cron':
            run_terminate_cron_lambda(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'sns':
            run_terminate_sns_lambda(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'sqs':
            run_terminate_sqs_lambda(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'event':
            run_terminate_event_lambda(lambda_env['NAME'], lambda_env)
            continue
        print('"%s" is not supported' % lambda_env['TYPE'])
        raise Exception()
    terminate_iam_for_lambda('sqs')
    terminate_iam_for_lambda('default')
