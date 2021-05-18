#!/usr/bin/env python3
import re
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_create_lambda_cron import run_create_lambda_cron
from run_create_lambda_default import run_create_lambda_default
from run_create_lambda_event import run_create_lambda_event
from run_create_lambda_iam import create_iam_for_lambda
from run_create_lambda_ses_sqs import run_create_lambda_ses_sqs
from run_create_lambda_sns import run_create_lambda_sns
from run_create_lambda_sqs import run_create_lambda_sqs

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()

################################################################################
#
# start
#
################################################################################
print_session('create lambda')

################################################################################

lambdas_list = env['lambda']
if len(args) == 2:
    target_lambda_name = args[1]
    target_lambda_name_exists = False
    for lambda_env in lambdas_list:
        if lambda_env['NAME'] == target_lambda_name:
            target_lambda_name_exists = True
            if lambda_env['TYPE'] == 'default':
                run_create_lambda_default(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'cron':
                run_create_lambda_cron(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'sns':
                run_create_lambda_sns(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'sqs':
                run_create_lambda_sqs(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'ses_sqs':
                run_create_lambda_ses_sqs(lambda_env['NAME'], lambda_env)
                break
            if lambda_env['TYPE'] == 'event':
                run_create_lambda_event(lambda_env['NAME'], lambda_env)
                break
            print('"%s" is not supported' % lambda_env['TYPE'])
            raise Exception()
    if not target_lambda_name_exists:
        print('"%s" is not exists in config.json' % target_lambda_name)
else:
    role_created = False
    for lambda_env in lambdas_list:
        git_url = lambda_env['GIT_URL']
        mm = re.match(r'^.+/(.+)\.git$', git_url)
        if not mm:
            raise Exception()
        git_folder_name = mm.group(1)
        rr = create_iam_for_lambda(git_folder_name, lambda_env['NAME'])
        if rr:
            role_created = rr

    if role_created:
        print_message('wait 120 seconds to let iam role and policy propagated to all regions...')
        time.sleep(120)

    for lambda_env in lambdas_list:
        if lambda_env['TYPE'] == 'default':
            run_create_lambda_default(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'cron':
            run_create_lambda_cron(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'sns':
            run_create_lambda_sns(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'sqs':
            run_create_lambda_sqs(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'ses_sqs':
            run_create_lambda_ses_sqs(lambda_env['NAME'], lambda_env)
            continue
        if lambda_env['TYPE'] == 'event':
            run_create_lambda_event(lambda_env['NAME'], lambda_env)
            break
        print('"%s" is not supported' % lambda_env['TYPE'])
        raise Exception()
