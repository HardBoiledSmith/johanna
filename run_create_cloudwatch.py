#!/usr/bin/env python3

from env import env
from run_common import check_template_availability
from run_common import print_session
from run_create_cloudwatch_dashboard import run_create_cloudwatch_dashboard

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

################################################################################
#
# start
#
################################################################################
print_session('create cw')

################################################################################
check_template_availability()

cw = env['cloudwatch']
target_cw_name = None
region = None
check_exists = False

if len(args) > 1:
    target_cw_name = args[1]

if len(args) > 2:
    region = args[2]

for cw_env in cw['ENVIRONMENTS']:
    if target_cw_name and cw_env['NAME'] != target_cw_name:
        continue

    if region and cw_env.get('AWS_DEFAULT_REGION') != region:
        continue

    if target_cw_name:
        check_exists = True

    if cw_env['TYPE'] == 'dashboard':
        run_create_cloudwatch_dashboard(cw_env['NAME'], cw_env)
    else:
        print('"%s" is not supported' % cw_env['TYPE'])
        raise Exception()

if not check_exists and target_cw_name and not region:
    print('"%s" is not exists in config.json' % target_cw_name)

if not check_exists and target_cw_name and region:
    print('"%s, %s" is not exists in config.json' % (target_cw_name, region))
