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


def run_terminate_alarm_widget_in_dashboard(name, settings):
    phase = env['common']['PHASE']
    alarm_region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(alarm_region)
    dashboard_name = '%s_%s' % (name, alarm_region)
    alarm_name = '%s-%s_%s_%s' % (phase, name, alarm_region, settings['METRIC_NAME'])

    try:
        cmd = ['cloudwatch', 'get-dashboard']
        cmd += ['--dashboard-name', dashboard_name]
        rr = aws_cli.run(cmd)
        widgets = json.loads(rr['DashboardBody'])['widgets']

        cmd = ['cloudwatch', 'delete-dashboards']
        cmd += ['--dashboard-name', dashboard_name]
        aws_cli.run(cmd)
    except Exception:
        return

    new_widget = [ww for ww in widgets if ww['properties']['title'] == alarm_name]
    if len(new_widget) == 0:
        return

    for (ii, ww) in enumerate(new_widget):
        y = ii // 3 * 6
        x = ii % 3 * 6
        ww['properties']['x'] = x
        ww['properties']['y'] = y

    cmd = ['cloudwatch', 'put-dashboard']
    cmd += ['--dashboard-name', dashboard_name]
    cmd += ['--dashboard-body', json.dumps({
        'widgets': new_widget
    })]
    aws_cli.run(cmd)


def run_terminate_cw_alarm(name, settings):
    phase = env['common']['PHASE']
    region = settings['AWS_DEFAULT_REGION']
    aws_cli = AWSCli(region)

    ################################################################################
    alarm_name = '%s-%s_%s_%s' % (phase, name, region, settings['METRIC_NAME'])

    if settings['TYPE'] == 'sqs':
        sqs_name = settings['QUEUE_NAME']
        alarm_name = '%s-%s_%s_%s_%s' % (phase, name, region, sqs_name, settings['METRIC_NAME'])

    print_message('terminate cloudwatch alarm: %s' % alarm_name)

    cmd = ['cloudwatch', 'delete-alarms']
    cmd += ['--alarm-names', alarm_name]
    aws_cli.run(cmd, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate cloudwatch alarm')

cw = env.get('cloudwatch', dict())

if len(args) == 2:
    target_cw_alarm_name = args[1]
    target_cw_alarm_name_exists = False

    for cw_alarm_env in cw.get('ALARMS', list()):
        if cw_alarm_env['NAME'] == target_cw_alarm_name:
            target_cw_alarm_name_exists = True
            run_terminate_cw_alarm(cw_alarm_env['NAME'], cw_alarm_env)
            run_terminate_alarm_widget_in_dashboard(cw_alarm_env['NAME'], cw_alarm_env)
    if not target_cw_alarm_name_exists:
        print('"%s" is not exists in config.json' % target_cw_alarm_name)
else:
    for cw_alarm_env in cw.get('ALARMS', list()):
        run_terminate_cw_alarm(cw_alarm_env['NAME'], cw_alarm_env)
