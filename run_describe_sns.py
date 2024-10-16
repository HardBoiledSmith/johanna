#!/usr/bin/env python3.12
from env import env
from run_common import AWSCli

aws_cli = AWSCli()


def describe_sns_topic():
    if not env.get('sns'):
        return False

    topic_name_list = list()
    sns_list = env['sns']
    for sl in sns_list:
        if sl['TYPE'] == 'topic':
            topic_name_list.append(sl['NAME'])

    cmd = ['sns', 'list-topics']
    result = aws_cli.run(cmd)

    for topic in result['Topics']:
        for tname in topic_name_list:
            suffix = ':%s' % tname
            # noinspection PyTypeChecker
            arn = topic['TopicArn']
            if arn.endswith(suffix):
                return True

    return False


results = list()

if describe_sns_topic():
    results.append('SNS Topic -------------- O')
else:
    results.append('SNS Topic -------------- X')

print('#' * 80)

for r in results:
    print(r)

print('#' * 80)
