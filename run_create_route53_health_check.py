#!/usr/bin/env python3.12

import json
import re
import time
from datetime import datetime

from env import env
from run_common import AWSCli
from run_common import parse_args
from run_common import print_message


def _create_route53_health_check_and_alarm(domain, settings, unique_domain=None):
    aws_cli = AWSCli()
    name = settings['NAME']
    protocol_type = settings.get('PROTOCOL_TYPE', 'HTTPS')

    print_message('create Route53 health check: %s' % name)

    match = re.search(r'(.*):(\d+)$', domain)
    port = 443
    if match:
        domain = match.group(1)
        port = int(match.group(2))

    dd = dict()
    dd['ResourcePath'] = settings['RESOURCEPATH']
    dd['RequestInterval'] = settings.get('REQUEST_INTERVAL', 30)
    dd['FailureThreshold'] = settings.get('FAILURE_THRESHOLD', 3)
    dd['MeasureLatency'] = False
    dd['Inverted'] = False
    dd['Disabled'] = False
    dd['EnableSNI'] = True
    dd['Regions'] = ["ap-northeast-1", "us-east-1", "ap-southeast-2"]
    dd['Port'] = port
    dd['FullyQualifiedDomainName'] = domain
    dd['Type'] = protocol_type
    if protocol_type == 'HTTP':
        dd['EnableSNI'] = False

    cmd = ['route53', 'create-health-check']
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M')
    caller_reference = f'{name}-{timestamp}' if not unique_domain else f'{name}-{domain}-{port}-{timestamp}'
    cmd += ['--caller-reference', caller_reference]
    cmd += ['--health-check-config', json.dumps(dd)]
    rr = aws_cli.run(cmd)

    healthcheck_id = rr['HealthCheck']['Id']
    cmd = ['route53', 'change-tags-for-resource']
    cmd += ['--resource-id', healthcheck_id]
    cmd += ['--resource-type', 'healthcheck']
    cmd += ['--add-tags', f'Key=Name,Value={caller_reference}']
    aws_cli.run(cmd)

    healthcheck_region = 'us-east-1'
    aws_cli = AWSCli(healthcheck_region)

    alarm_name = f'{name}-{healthcheck_region}-{settings["METRIC_NAME"]}' if not unique_domain \
        else f'{name}-{healthcheck_region}-{domain}-{port}-{settings["METRIC_NAME"]}'
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


def create_route53_health_check(settings):
    if settings.get('TARGETDOMAINNAME'):
        domain = settings['TARGETDOMAINNAME']
        _create_route53_health_check_and_alarm(domain, settings)
    elif settings.get('TARGETDOMAINNAME_LIST'):
        ll = settings['TARGETDOMAINNAME_LIST'].split(',')
        for domain in ll:
            _create_route53_health_check_and_alarm(domain, settings, True)
    else:
        print_message(f"[SKIPPED] {settings['NAME']}: TARGETDOMAINNAME or TARGETDOMAINNAME_LIST is not set")


################################################################################
#
# start
#
################################################################################
if __name__ == '__main__':
    _, args = parse_args()

    target_found = False
    target_name = None
    if len(args) > 1:
        target_name = args[1]

    for settings in env.get('route53', list()):
        if target_name and settings['NAME'] != target_name:
            continue

        target_found = True
        create_route53_health_check(settings)

    if not target_found:
        print_message('target not found')
