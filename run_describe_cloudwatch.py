#!/usr/bin/env python3
from env import env
from run_common import AWSCli

aws_cli = AWSCli()


def describe_cloudwatch_dashboard():
    if not env.get('cloudwatch'):
        return False

    if not env['cloudwatch'].get('DASHBOARDS'):
        return False

    d_set = set()
    dashboards_list = env['cloudwatch']['DASHBOARDS']
    for dl in dashboards_list:
        d_name = '%s_%s' % (dl['NAME'], dl['AWS_DEFAULT_REGION'])
        d_set.add(d_name)

    cmd = ['cloudwatch', 'list-dashboards']
    result = aws_cli.run(cmd)

    for de in result['DashboardEntries']:
        if de['DashboardName'] in d_set:
            return True

    return False


results = list()

if describe_cloudwatch_dashboard():
    results.append('CloudWatch Dashboard -------------- O')
else:
    results.append('CloudWatch Dashboard -------------- X')

print('#' * 80)

for r in results:
    print(r)

print('#' * 80)
