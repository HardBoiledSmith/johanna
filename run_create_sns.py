#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()


def run_create_sns_topic(name, settings):
    region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(region)

    ################################################################################
    print_message('create sns topic: %s' % name)

    cmd = ['sns', 'create-topic']
    cmd += ['--name', name]
    result = aws_cli.run(cmd)
    print('created:', result['TopicArn'])

    if 'EMAIL' in settings:
        print_message('create an email subscription for sns topic: %s' % name)
        cmd = ['sns', 'subscribe']
        cmd += ['--topic-arn', result['TopicArn']]
        cmd += ['--protocol', 'email']
        cmd += ['--notification-endpoint', settings['EMAIL']]
        aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('create sns')

sns_list = env.get('sns', list())
for sns_env in sns_list:
    if sns_env['TYPE'] == 'topic':
        run_create_sns_topic(sns_env['NAME'], sns_env)
