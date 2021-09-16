#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_create_sns_topic(name, settings):
    aws_cli = AWSCli(settings['AWS_REGION'])

    print_message(f'create sns topic: {name}')

    cmd = ['sns', 'create-topic']
    cmd += ['--name', name]
    result = aws_cli.run(cmd)
    print('created:', result['TopicArn'])

    if 'EMAIL' in settings:
        print_message(f'create an email subscription for sns topic: {name}')
        cmd = ['sns', 'subscribe']
        cmd += ['--topic-arn', result['TopicArn']]
        cmd += ['--protocol', 'email']
        cmd += ['--notification-endpoint', settings['EMAIL']]
        aws_cli.run(cmd)

    if 'PAGERDUTYAPPKEY' in settings and settings['PAGERDUTYAPPKEY']:
        print_message(f'create an email subscription for sns topic: {name}')
        cmd = ['sns', 'subscribe']
        cmd += ['--topic-arn', result['TopicArn']]
        cmd += ['--protocol', 'https']
        cmd += ['--notification-endpoint', settings['PAGERDUTYAPPKEY']]
        aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('create sns')

target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in env.get('sns', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True

    if settings['TYPE'] == 'topic':
        run_create_sns_topic(settings['NAME'], settings)
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
    print(f'sns: {mm} is not found in config.json')
