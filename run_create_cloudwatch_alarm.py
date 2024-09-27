#!/usr/bin/env python3.11
import json

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import reset_template_dir

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_create_cloudwatch_alarm_lambda(name, settings):
    phase = env['common']['PHASE']
    alarm_region = settings['AWS_REGION']
    aws_cli = AWSCli(alarm_region)

    alarm_name = '%s-%s_%s_%s' % (phase, name, alarm_region, 'NotSuccessIn5Min')

    topic_arn = aws_cli.get_topic_arn(settings['SNS_TOPIC_NAME'])
    if not topic_arn:
        print('sns topic: "%s" is not exists in %s' % (settings['SNS_TOPIC_NAME'], alarm_region))
        raise Exception()

    metrics = list()
    dd = dict()
    dd['Id'] = 'errors'
    dd['MetricStat'] = dict()
    dd['MetricStat']['Metric'] = dict()
    dd['MetricStat']['Metric']['Dimensions'] = list()
    dd['MetricStat']['Metric']['MetricName'] = 'Errors'
    dd['MetricStat']['Metric']['Namespace'] = 'AWS/Lambda'
    dd['MetricStat']['Period'] = 60 * 5
    dd['MetricStat']['Stat'] = 'Maximum'
    dd['ReturnData'] = True
    metrics.append(dd)

    cmd = ['cloudwatch', 'put-metric-alarm']
    cmd += ['--alarm-actions', topic_arn]
    cmd += ['--alarm-description', settings['DESCRIPTION']]
    cmd += ['--alarm-name', alarm_name]
    cmd += ['--comparison-operator', settings['COMPARISON_OPERATOR']]
    cmd += ['--datapoints-to-alarm', settings['DATAPOINTS_TO_ALARM']]
    cmd += ['--evaluation-periods', settings['EVALUATION_PERIODS']]
    cmd += ['--metrics', json.dumps(metrics)]
    cmd += ['--threshold', settings['THRESHOLD']]
    aws_cli.run(cmd)


def run_create_cloudwatch_alarm_elasticbeanstalk(name, settings):
    phase = env['common']['PHASE']
    alarm_region = settings['AWS_REGION']
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
    if 'INSUFFICIENT_DATA_ACTIONS' in settings:
        cmd += ['--treat-missing-data', settings['INSUFFICIENT_DATA_ACTIONS']]
    aws_cli.run(cmd)


def run_create_cloudwatch_alarm_rds(name, settings):
    phase = env['common']['PHASE']
    alarm_region = settings['AWS_REGION']
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
    alarm_region = settings['AWS_REGION']
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


def run_create_cloudwatch_alarm_sns(name, settings):
    phase = env['common']['PHASE']
    alarm_region = settings['AWS_REGION']
    aws_cli = AWSCli(alarm_region)

    alarm_name = '%s-%s_%s_%s' % (phase, name, alarm_region, settings['METRIC_NAME'])
    print_message('create or update cloudwatch alarm: %s' % alarm_name)

    topic_arn = aws_cli.get_topic_arn(settings['SNS_TOPIC_NAME'])
    if not topic_arn:
        print('sns topic: "%s" is not exists in %s' % (settings['SNS_TOPIC_NAME'], alarm_region))
        raise Exception()

    dimensions = list()
    for ii in settings['DIMENSIONS']:
        dd = dict()
        dd['Name'] = ii['name']
        dd['Value'] = ii['value']
        dimensions.append(dd)

    cmd = ['cloudwatch', 'put-metric-alarm']
    cmd += ['--alarm-actions', topic_arn]
    cmd += ['--alarm-description', settings['DESCRIPTION']]
    cmd += ['--alarm-name', alarm_name]
    cmd += ['--comparison-operator', settings['COMPARISON_OPERATOR']]
    cmd += ['--datapoints-to-alarm', settings['DATAPOINTS_TO_ALARM']]
    cmd += ['--dimensions', json.dumps(dimensions)]
    cmd += ['--evaluation-periods', settings['EVALUATION_PERIODS']]
    cmd += ['--metric-name', settings['METRIC_NAME']]
    cmd += ['--namespace', settings['NAMESPACE']]
    cmd += ['--period', settings['PERIOD']]
    cmd += ['--statistic', settings['STATISTIC']]
    cmd += ['--threshold', settings['THRESHOLD']]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('create cloudwatch alarm')

reset_template_dir(options)

cw = env.get('cloudwatch', dict())
target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in cw.get('ALARMS', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True

    if settings['TYPE'] == 'elasticbeanstalk':
        run_create_cloudwatch_alarm_elasticbeanstalk(settings['NAME'], settings)
    elif settings['TYPE'] == 'rds':
        run_create_cloudwatch_alarm_rds(settings['NAME'], settings)
    elif settings['TYPE'] == 'sqs':
        run_create_cloudwatch_alarm_sqs(settings['NAME'], settings)
    elif settings['TYPE'] == 'lambda':
        run_create_cloudwatch_alarm_lambda(settings['NAME'], settings)
    elif settings['TYPE'] == 'sns':
        run_create_cloudwatch_alarm_sns(settings['NAME'], settings)
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
    print(f'cloudwatch alarm: {mm} is not found in config.json')
