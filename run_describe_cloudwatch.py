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


def describe_cloudwatch_alarm():
    if not env.get('cloudwatch'):
        return False

    if not env['cloudwatch'].get('ALARMS'):
        return False

    a_set = set()
    alarms_list = env['cloudwatch']['ALARMS']
    for al in alarms_list:
        a_name = '%s_%s_%s' % (al['NAME'], al['AWS_DEFAULT_REGION'], al['METRIC_NAME'])
        a_set.add(a_name)

    cmd = ['cloudwatch', 'describe-alarms']
    cmd += ['--alarm-names', ' '.join(a_set)]
    result = aws_cli.run(cmd)

    for ma in result['MetricAlarms']:
        if ma['AlarmName'] in a_set:
            return True

    return False


results = list()

if describe_cloudwatch_dashboard():
    results.append('CloudWatch Dashboard -------------- O')
else:
    results.append('CloudWatch Dashboard -------------- X')

if describe_cloudwatch_alarm():
    results.append('CloudWatch Alarm -------------- O')
else:
    results.append('CloudWatch Alarm -------------- X')

print('#' * 80)

for r in results:
    print(r)

print('#' * 80)
