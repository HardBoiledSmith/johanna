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


def run_create_cloudwatch_alarm_elasticbeanstalk(name, settings):
    phase = env['common']['PHASE']
    alarm_region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(alarm_region)

    print_message('get elasticbeanstalk environment info: %s' % name)

    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--no-include-deleted']
    result = aws_cli.run(cmd)

    env_list = list()
    for ee in result['Environments']:
        cname = ee['CNAME']
        if not cname.endswith('%s.elasticbeanstalk.com' % alarm_region):
            continue
        if '%s.' % name not in cname and '%s2.' % name not in cname:
            continue
        ename = ee['EnvironmentName']
        if ename.startswith(name):
            env_list.append(ee)

    env_instances_list = list()
    env_asg_list = list()
    env_elb_list = list()

    for ee in env_list:
        cmd = ['elasticbeanstalk', 'describe-environment-resources']
        cmd += ['--environment-id', ee['EnvironmentId']]
        result = aws_cli.run(cmd)
        ee_res = result['EnvironmentResources']
        for instance in ee_res['Instances']:
            ii = dict()
            ii['Id'] = instance['Id']
            ii['EnvironmentName'] = ee_res['EnvironmentName']
            env_instances_list.append(ii)
        for asg in ee_res['AutoScalingGroups']:
            env_asg_list.append(asg)
        for elb in ee_res['LoadBalancers']:
            env_elb_list.append(elb)

    ################################################################################
    alarm_name = '%s-%s_%s_%s' % (phase, name, alarm_region, settings['METRIC_NAME'])
    print_message('create or update cloudwatch alarm: %s' % alarm_name)

    topic_arn = aws_cli.get_topic_arn(settings['SNS_TOPIC_NAME'])
    if not topic_arn:
        print('sns topic: "%s" is not exists in %s' % (settings['SNS_TOPIC_NAME'], alarm_region))
        raise Exception()

    dimension_list = list()
    for ei in env_instances_list:
        if settings['DIMENSIONS'] == 'InstanceId':
            dimension = 'Name=InstanceId,Value=%s' % ei['Id']
            dimension_list.append(dimension)
        if settings['DIMENSIONS'] == 'EnvironmentName':
            dimension = 'Name=EnvironmentName,Value=%s' % ei['EnvironmentName']
            dimension_list.append(dimension)
            break

    for ei in env_asg_list:
        if settings['DIMENSIONS'] == 'AutoScalingGroupName':
            dimension = 'Name=AutoScalingGroupName,Value=%s' % ei['Name']
            dimension_list.append(dimension)

    for ei in env_elb_list:
        if settings['DIMENSIONS'] == 'LoadBalancerName':
            dimension = 'Name=LoadBalancerName,Value=%s' % ei['Name']
            dimension_list.append(dimension)

    cmd = ['cloudwatch', 'put-metric-alarm']
    cmd += ['--alarm-actions', topic_arn]
    cmd += ['--alarm-description', settings['DESCRIPTION']]
    cmd += ['--alarm-name', alarm_name]
    cmd += ['--comparison-operator', settings['COMPARISON_OPERATOR']]
    cmd += ['--datapoints-to-alarm', settings['DATAPOINTS_TO_ALARM']]
    cmd += ['--dimensions', ' '.join(dimension_list)]
    cmd += ['--evaluation-periods', settings['EVALUATION_PERIODS']]
    cmd += ['--metric-name', settings['METRIC_NAME']]
    cmd += ['--namespace', settings['NAMESPACE']]
    cmd += ['--period', settings['PERIOD']]
    cmd += ['--statistic', settings['STATISTIC']]
    cmd += ['--threshold', settings['THRESHOLD']]
    aws_cli.run(cmd)


def run_create_cloudwatch_alarm_rds(name, settings):
    phase = env['common']['PHASE']
    alarm_region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(alarm_region)

    alarm_name = '%s-%s_%s_%s' % (phase, name, alarm_region, settings['METRIC_NAME'])
    print_message('create or update cloudwatch alarm: %s' % alarm_name)

    topic_arn = aws_cli.get_topic_arn(settings['SNS_TOPIC_NAME'])
    if not topic_arn:
        print('sns topic: "%s" is not exists in %s' % (settings['SNS_TOPIC_NAME'], alarm_region))
        raise Exception()

    dimension_list = list()
    if settings['DIMENSIONS'] == 'DBClusterIdentifier':
        db_cluster_id = env['rds']['DB_CLUSTER_ID']
        dimension = 'Name=DBClusterIdentifier,Value=%s' % db_cluster_id
        dimension_list.append(dimension)

    cmd = ['cloudwatch', 'put-metric-alarm']
    cmd += ['--alarm-actions', topic_arn]
    cmd += ['--alarm-description', settings['DESCRIPTION']]
    cmd += ['--alarm-name', alarm_name]
    cmd += ['--comparison-operator', settings['COMPARISON_OPERATOR']]
    cmd += ['--datapoints-to-alarm', settings['DATAPOINTS_TO_ALARM']]
    cmd += ['--dimensions', ' '.join(dimension_list)]
    cmd += ['--evaluation-periods', settings['EVALUATION_PERIODS']]
    cmd += ['--metric-name', settings['METRIC_NAME']]
    cmd += ['--namespace', settings['NAMESPACE']]
    cmd += ['--period', settings['PERIOD']]
    cmd += ['--statistic', settings['STATISTIC']]
    cmd += ['--threshold', settings['THRESHOLD']]
    aws_cli.run(cmd)


def run_create_cloudwatch_alarm_sqs(name, settings):
    phase = env['common']['PHASE']
    alarm_region = settings['AWS_DEFAULT_REGION']
    sqs_name = settings['QUEUE_NAME']
    aws_cli = AWSCli(alarm_region)

    alarm_name = '%s-%s_%s_%s_%s' % (phase, name, alarm_region, sqs_name, settings['METRIC_NAME'])
    print_message('create or update cloudwatch alarm: %s' % alarm_name)

    topic_arn = aws_cli.get_topic_arn(settings['SNS_TOPIC_NAME'])
    if not topic_arn:
        print('sns topic: "%s" is not exists in %s' % (settings['SNS_TOPIC_NAME'], alarm_region))
        raise Exception()

    dimension_list = list()
    if settings['DIMENSIONS'] == 'QueueName':
        dimension = 'Name=QueueName,Value=%s' % sqs_name
        dimension_list.append(dimension)

    cmd = ['cloudwatch', 'put-metric-alarm']
    cmd += ['--alarm-actions', topic_arn]
    cmd += ['--alarm-description', settings['DESCRIPTION']]
    cmd += ['--alarm-name', alarm_name]
    cmd += ['--comparison-operator', settings['COMPARISON_OPERATOR']]
    cmd += ['--datapoints-to-alarm', settings['DATAPOINTS_TO_ALARM']]
    cmd += ['--dimensions', ' '.join(dimension_list)]
    cmd += ['--evaluation-periods', settings['EVALUATION_PERIODS']]
    cmd += ['--metric-name', settings['METRIC_NAME']]
    cmd += ['--namespace', settings['NAMESPACE']]
    cmd += ['--period', settings['PERIOD']]
    cmd += ['--statistic', settings['STATISTIC']]
    cmd += ['--threshold', settings['THRESHOLD']]
    aws_cli.run(cmd)


def run_create_alarm_widget_in_dashboard(name, settings):
    phase = env['common']['PHASE']
    alarm_region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(alarm_region)
    dashboard_name = '%s_%s' % (name, alarm_region)
    alarm_name = '%s-%s_%s_%s' % (phase, name, alarm_region, settings['METRIC_NAME'])

    is_exist_dashboard = False
    widgets = list()
    try:
        cmd = ['cloudwatch', 'get-dashboard']
        cmd += ['--dashboard-name', dashboard_name]
        rr = aws_cli.run(cmd)
        widgets = json.loads(rr['DashboardBody'])['widgets']
        is_exist_dashboard = True

        cmd = ['cloudwatch', 'delete-dashboards']
        cmd += ['--dashboard-name', dashboard_name]
        aws_cli.run(cmd)
    except Exception:
        pass

    for ww in widgets:
        if ww['properties']['title'] == alarm_name:
            return

    cmd = ['cloudwatch', 'describe-alarms']
    cmd += ['--alarm-names', alarm_name]
    rr = aws_cli.run(cmd)
    alarm_arn = rr['MetricAlarms'][0]['AlarmArn']

    x = 0
    y = 0
    if is_exist_dashboard:
        new_wi = len(widgets)
        y = new_wi // 3 * 6
        x = new_wi % 3 * 6

    widgets.append({
        "height": 6,
        "properties": {
            "title": alarm_name,
            "annotations": {
                "alarms": [
                    alarm_arn
                ]
            },
            "view": "timeSeries",
            "stacked": False
        },
        "type": "metric",
        "width": 6,
        "x": x,
        "y": y
    })

    cmd = ['cloudwatch', 'put-dashboard']
    cmd += ['--dashboard-name', dashboard_name]
    cmd += ['--dashboard-body', json.dumps({
        'widgets': widgets
    })]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('create cloudwatch alarm')

cw = env.get('cloudwatch', dict())
target_cw_alarm_name = None
region = None
check_exists = False

if len(args) > 1:
    target_cw_alarm_name = args[1]

if len(args) > 2:
    region = args[2]

for cw_alarm_env in cw.get('ALARMS', list()):
    if target_cw_alarm_name and cw_alarm_env['NAME'] != target_cw_alarm_name:
        continue

    if region and cw_alarm_env.get('AWS_DEFAULT_REGION') != region:
        continue

    if target_cw_alarm_name:
        check_exists = True

    if cw_alarm_env['TYPE'] == 'elasticbeanstalk':
        run_create_cloudwatch_alarm_elasticbeanstalk(cw_alarm_env['NAME'], cw_alarm_env)
        run_create_alarm_widget_in_dashboard(cw_alarm_env['NAME'], cw_alarm_env)
    elif cw_alarm_env['TYPE'] == 'rds':
        run_create_cloudwatch_alarm_rds(cw_alarm_env['NAME'], cw_alarm_env)
        run_create_alarm_widget_in_dashboard(cw_alarm_env['NAME'], cw_alarm_env)
    elif cw_alarm_env['TYPE'] == 'sqs':
        run_create_cloudwatch_alarm_sqs(cw_alarm_env['NAME'], cw_alarm_env)
        run_create_alarm_widget_in_dashboard(cw_alarm_env['NAME'], cw_alarm_env)
    else:
        print('"%s" is not supported' % cw_alarm_env['TYPE'])
        raise Exception()

if not check_exists and target_cw_alarm_name and not region:
    print('"%s" is not exists in config.json' % target_cw_alarm_name)

if not check_exists and target_cw_alarm_name and region:
    print('"%s, %s" is not exists in config.json' % (target_cw_alarm_name, region))
