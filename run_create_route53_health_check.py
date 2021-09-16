#!/usr/bin/env python3

import json
from datetime import datetime
import time

from run_common import AWSCli
from run_common import parse_args
from env import env
from run_common import print_message


def create_route53_health_check(settings):

    aws_cli = AWSCli()
    name = settings['NAME']

    cmd = ['route53', 'create-health-check']
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M')
    caller_reference = f'{name}-{timestamp}'
    cmd += ['--caller-reference', caller_reference]

    dd = {
        "Port": 443,
        "Type": "HTTPS",
        "ResourcePath": settings['RESOURCEPATH'],
        "FullyQualifiedDomainName": settings['TARGETDOMAINNAME'],
        "RequestInterval": 30,
        "FailureThreshold": 3,
        "MeasureLatency": False,
        "Inverted": False,
        "Disabled": False,
        "EnableSNI": True,
        "Regions": ["us-east-1", "us-west-1", "us-west-2", "eu-west-1", "ap-southeast-1", "ap-southeast-2",
                    "ap-northeast-1", "sa-east-1"]
    }

    cmd += ['--health-check-config', json.dumps(dd)]
    rr = aws_cli.run(cmd)
    print(rr)

    healthcheck_id = rr['HealthCheck']['Id']
    cmd = ['route53', 'change-tags-for-resource']
    cmd += ['--resource-id', healthcheck_id]
    cmd += ['--resource-type', 'healthcheck']
    cmd += ['--add-tags', f'Key=Name,Value={caller_reference}']
    aws_cli.run(cmd)

    healthcheck_region = 'us-east-1'
    aws_cli = AWSCli(healthcheck_region)

    alarm_name = f'{name}-{healthcheck_region}-{settings["METRIC_NAME"]}'
    print_message('create or update cloudwatch alarm: %s' % alarm_name)

    time.sleep(5)

    topic_arn = aws_cli.get_topic_arn(settings['SNS_TOPIC_NAME'])
    if not topic_arn:
        print(f'sns topic: "{settings["SNS_TOPIC_NAME"]}" is not exists in us-east-1')
        raise Exception()

    cmd = ['cloudwatch', 'put-metric-alarm']
    cmd += ['--alarm-actions', topic_arn]
    cmd += ['--alarm-description', settings['DESCRIPTION']]
    cmd += ['--alarm-name', alarm_name]
    cmd += ['--comparison-operator', settings['COMPARISON_OPERATOR']]
    cmd += ['--datapoints-to-alarm', settings['DATAPOINTS_TO_ALARM']]
    cmd += ['--dimensions', f'Name=HealthCheckId,Value={healthcheck_id}']
    cmd += ['--evaluation-periods', settings['EVALUATION_PERIODS']]
    cmd += ['--metric-name', settings['METRIC_NAME']]
    cmd += ['--namespace', settings['NAMESPACE']]
    cmd += ['--period', settings['PERIOD']]
    cmd += ['--statistic', settings['STATISTIC']]
    cmd += ['--threshold', settings['THRESHOLD']]
    if 'INSUFFICIENT_DATA_ACTIONS' in settings:
        cmd += ['--treat-missing-data', settings['INSUFFICIENT_DATA_ACTIONS']]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
if __name__ == '__main__':
    args = parse_args()

    for settings in env.get('route53', list()):

        create_route53_health_check(settings)
