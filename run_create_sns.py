#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

aws_cli = AWSCli()


def run_create_sns_topic(name):
    ################################################################################
    print_message('create sns topic: %s' % name)

    cmd = ['sns', 'create-topic']
    cmd += ['--name', name]
    result = aws_cli.run(cmd)
    print('created:', result['TopicArn'])


################################################################################
#
# start
#
################################################################################
print_session('create sns')

sns_list = env.get('sns', list())
for sns_env in sns_list:
    if sns_env['TYPE'] == 'topic':
        run_create_sns_topic(sns_env['NAME'])
