#!/usr/bin/env python3

from env import env
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def run_terminate_client_vpn(settings):
    print_message(f'terminate {settings["NAME"]}')


################################################################################
#
# start
#
################################################################################
print_session('terminate client vpn')

################################################################################

target_name = None
region = None
check_exists = False

if len(args) > 1:
    target_name = args[1]

if len(args) > 2:
    region = args[2]

for vpn_env in env['client_vpn']:
    if target_name and vpn_env['NAME'] != target_name:
        continue

    if region and vpn_env.get('AWS_DEFAULT_REGION') != region:
        continue

    if target_name:
        check_exists = True

    run_terminate_client_vpn(vpn_env)

if not check_exists and target_name:
    print(f'{target_name} is not exists in config.json')

# run_terminate_iam_for_client_vpn()
