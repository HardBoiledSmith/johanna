#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import parse_args


def delete_route53_health_check(settings):
    aws_cli = AWSCli()
    name = settings['NAME']

    cmd = ['route53', 'list-health-checks']
    rr = aws_cli.run(cmd)

    for r in rr['HealthChecks']:
        if r['CallerReference'].startswith(name):
            cmd = ['route53', 'delete-health-check']
            cmd += ['--health-check-id', r['Id']]
            aws_cli.run(cmd)

            healthcheck_region = 'us-east-1'
            aws_cli = AWSCli(healthcheck_region)
            alarm_name = f'{name}-{healthcheck_region}-{settings["METRIC_NAME"]}'
            cmd = ['cloudwatch', 'delete-alarms']
            cmd += ['--alarm-names', alarm_name]
            aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################

if __name__ == '__main__':
    args = parse_args()

    for settings in env.get('route53', list()):
        delete_route53_health_check(settings)
