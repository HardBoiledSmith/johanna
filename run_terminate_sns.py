#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def run_terminate_sns_tpoic(name, settings):
    region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(region)

    ################################################################################
    print_message('terminate sns topic subscriptions')

    topic_arn = aws_cli.get_topic_arn(name)
    cmd = ['sns', 'list-subscriptions-by-topic']
    cmd += ['--topic-arn', topic_arn]
    rr = aws_cli.run(cmd)

    for ss in rr['Subscriptions']:
        cmd = ['sns', 'list-subscriptions']
        cmd += ['--subscription-arn', ss['SubscriptionArn']]
        aws_cli.run(cmd)

    print_message('terminate sns topic: "%s" in %s' % (name, region))

    if not topic_arn:
        return

    cmd = ['sns', 'delete-topic']
    cmd += ['--topic-arn', topic_arn]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('terminate sns')

sns_list = env.get('sns', list())

for sns_env in sns_list:
    if sns_env['TYPE'] == 'topic':
        run_terminate_sns_tpoic(sns_env['NAME'], sns_env)
