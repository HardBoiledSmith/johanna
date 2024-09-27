#!/usr/bin/env python3.11

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_terminate_sns_tpoic(name, settings):
    aws_cli = AWSCli(settings['AWS_REGION'])

    ################################################################################
    print_message('terminate sns topic subscriptions')

    topic_arn = aws_cli.get_topic_arn(name)

    if not topic_arn:
        return

    cmd = ['sns', 'list-subscriptions-by-topic']
    cmd += ['--topic-arn', topic_arn]
    rr = aws_cli.run(cmd)

    for ss in rr['Subscriptions']:
        cmd = ['sns', 'unsubscribe']
        cmd += ['--subscription-arn', ss['SubscriptionArn']]
        aws_cli.run(cmd, ignore_error=True)

    print_message(f'terminate sns topic: {name}')

    cmd = ['sns', 'delete-topic']
    cmd += ['--topic-arn', topic_arn]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('terminate sns')

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
        run_terminate_sns_tpoic(settings['NAME'], settings)
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
