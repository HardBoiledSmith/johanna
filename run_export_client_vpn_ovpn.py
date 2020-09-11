#!/usr/bin/env python3
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def run_export_new_client_ovpn(settings, email):
    vpc_region = settings['AWS_VPC_REGION']
    aws_cli = AWSCli(vpc_region)
    print_message(f'create new {settings["NAME"]} .ovpn file for {email}')

    ################################################################################
    print_message('get endpoint id')

    cmd = ['ec2', 'describe-client-vpn-endpoints']
    result = aws_cli.run(cmd)

    vpn_endpoint_id = None
    for r in result['ClientVpnEndpoints']:
        if not r['Tags']:
            continue

        for t in r['Tags']:
            if t['Key'] == 'Name' and t['Value'] == settings['NAME']:
                vpn_endpoint_id = r['ClientVpnEndpointId']
                break

        if vpn_endpoint_id:
            break

    if not vpn_endpoint_id:
        print('ERROR!!! No client vpn endpoint found')
        raise Exception()

    ################################################################################
    print_message('generate new client key pairs')





################################################################################
#
# start
#
################################################################################
print_session('export ovpn files for client vpn')

################################################################################

check_exists = False

if len(args) != 3:
    print('usage:', args[0], '<name> <region> <user-email>')
    raise Exception()

target_name = args[1]
region = args[2]
email = args[3]

for vpn_env in env['client_vpn']:
    if vpn_env['NAME'] != target_name:
        continue

    if vpn_env.get('AWS_VPC_REGION') != region:
        continue

    run_export_new_client_ovpn(vpn_env, email)

if not check_exists and target_name:
    print(f'{target_name} is not exists in config.json')
