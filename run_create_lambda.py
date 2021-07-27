#!/usr/bin/env python3

from env import env
from run_common import print_session
from run_create_lambda_cron import run_create_lambda_cron
from run_create_lambda_default import run_create_lambda_default
from run_create_lambda_event import run_create_lambda_event
from run_create_lambda_ses_sqs import run_create_lambda_ses_sqs
from run_create_lambda_sns import run_create_lambda_sns
from run_create_lambda_sqs import run_create_lambda_sqs

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()

################################################################################
#
# start
#
################################################################################
print_session('create lambda')

target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in env.get('lambda', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if region and settings['AWS_REGION'] != region:
        continue

    is_target_exists = True

    if settings['TYPE'] == 'default':
        run_create_lambda_default(settings['NAME'], settings, options)
    elif settings['TYPE'] == 'cron':
        run_create_lambda_cron(settings['NAME'], settings, options)
    elif settings['TYPE'] == 'sns':
        run_create_lambda_sns(settings['NAME'], settings, options)
    elif settings['TYPE'] == 'sqs':
        run_create_lambda_sqs(settings['NAME'], settings, options)
    elif settings['TYPE'] == 'ses_sqs':
        run_create_lambda_ses_sqs(settings['NAME'], settings, options)
    elif settings['TYPE'] == 'event':
        run_create_lambda_event(settings['NAME'], settings, options)
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
    print(f'lambda: {mm} is not found in config.json')
