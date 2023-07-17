#!/usr/bin/env python3

import re

from env import env
from run_common import AWSCli, print_message
from run_common import parse_args


def _delete_route53_health_check_and_alarm(domain, settings, unique_domain=None):
    aws_cli = AWSCli()
    name = settings['NAME']

    cmd = ['route53', 'list-health-checks']
    rr = aws_cli.run(cmd)

    match = re.search(r'(.*):(\d+)$', domain)
    port = 443
    if match:
        domain = match.group(1)
        port = int(match.group(2))

    for r in rr['HealthChecks']:
        if not r['CallerReference'].startswith(name):
            continue

        cmd = ['route53', 'delete-health-check']
        cmd += ['--health-check-id', r['Id']]
        aws_cli.run(cmd)

        healthcheck_region = 'us-east-1'
        aws_cli = AWSCli(healthcheck_region)
        alarm_name = f'{name}-{healthcheck_region}-{settings["METRIC_NAME"]}' if not unique_domain \
            else f'{name}-{healthcheck_region}-{domain}-{port}-{settings["METRIC_NAME"]}'
        cmd = ['cloudwatch', 'delete-alarms']
        cmd += ['--alarm-names', alarm_name]
        aws_cli.run(cmd)


def delete_route53_health_check(settings):
    if settings.get('TARGETDOMAINNAME'):
        domain = settings['TARGETDOMAINNAME']
        _delete_route53_health_check_and_alarm(domain, settings)
    elif settings.get('TARGETDOMAINNAME_LIST'):
        ll = settings['TARGETDOMAINNAME_LIST'].split(',')
        for domain in ll:
            _delete_route53_health_check_and_alarm(domain, settings, True)
    else:
        print_message(f"[SKIPPED] {settings['NAME']}: TARGETDOMAINNAME or TARGETDOMAINNAME_LIST is not set")


################################################################################
#
# start
#
################################################################################

if __name__ == '__main__':
    args = parse_args()

    for settings in env.get('route53', list()):
        delete_route53_health_check(settings)
