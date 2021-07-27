#!/usr/bin/env python3
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_terminate_client_vpn(name, settings):
    vpc_region = settings['AWS_VPC_REGION']
    aws_cli = AWSCli(vpc_region)
    print_message(f'terminate {name}')

    ################################################################################
    print_message('get endpoint id')

    cmd = ['ec2', 'describe-client-vpn-endpoints']
    result = aws_cli.run(cmd)

    vpn_endpoint_id = None
    for r in result['ClientVpnEndpoints']:
        if not r['Tags']:
            continue

        for t in r['Tags']:
            if t['Key'] == 'Name' and t['Value'] == name:
                vpn_endpoint_id = r['ClientVpnEndpointId']
                break

        if vpn_endpoint_id:
            break

    if not vpn_endpoint_id:
        return

    ################################################################################
    print_message('terminate all existing vpn connections')

    cmd = ['ec2', 'terminate-client-vpn-connections']
    cmd += ['--client-vpn-endpoint-id', vpn_endpoint_id]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('revoke authorizations for target network')

    cmd = ['ec2', 'revoke-client-vpn-ingress']
    cmd += ['--client-vpn-endpoint-id', vpn_endpoint_id]
    cmd += ['--target-network-cidr', aws_cli.cidr_vpc['eb']]
    cmd += ['--revoke-all-groups']
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['ec2', 'revoke-client-vpn-ingress']
    cmd += ['--client-vpn-endpoint-id', vpn_endpoint_id]
    cmd += ['--target-network-cidr', aws_cli.cidr_vpc['rds']]
    cmd += ['--revoke-all-groups']
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('disassociate target network')

    cmd = ['ec2', 'describe-client-vpn-target-networks']
    cmd += ['--client-vpn-endpoint-id', vpn_endpoint_id]
    result = aws_cli.run(cmd)

    for r in result['ClientVpnTargetNetworks']:
        cmd = ['ec2', 'disassociate-client-vpn-target-network']
        cmd += ['--client-vpn-endpoint-id', vpn_endpoint_id]
        cmd += ['--association-id', r['AssociationId']]
        aws_cli.run(cmd, ignore_error=True)

    elapsed_time = 0
    while True:
        cmd = ['ec2', 'describe-client-vpn-endpoints']
        cmd += ['--client-vpn-endpoint-ids', vpn_endpoint_id]
        result = aws_cli.run(cmd)

        result = result['ClientVpnEndpoints'][0]
        if result['Status']['Code'] == 'pending-associate':
            break

        print('waiting for endpoint disassociated... (elapsed time: \'%d\' seconds)' % elapsed_time)
        time.sleep(5)
        elapsed_time += 5

        if elapsed_time > 60 * 30:
            raise Exception()

    ################################################################################
    print_message('remove client vpn endpoint')

    cmd = ['ec2', 'delete-client-vpn-endpoint']
    cmd += ['--client-vpn-endpoint-id', vpn_endpoint_id]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete server certification')

    cmd = ['acm', 'list-certificates']
    result = aws_cli.run(cmd)

    for r in result['CertificateSummaryList']:
        if r['DomainName'] != 'server':
            continue

        cmd = ['acm', 'delete-certificate']
        cmd += ['--certificate-arn', r['CertificateArn']]
        aws_cli.run(cmd)

    ################################################################################
    print_message('delete SAML identity provider')

    cmd = ['iam', 'list-saml-providers']
    result = aws_cli.run(cmd)

    aa = None

    for r in result['SAMLProviderList']:
        if f'AWSClientVPN_SAML_{name}' in r['Arn']:
            aa = r['Arn']
            break

    if not aa:
        return

    cmd = ['iam', 'delete-saml-provider']
    cmd += ['--saml-provider-arn', aa]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('terminate client vpn')

################################################################################

target_name = None
region = options.get('region')
check_exists = False

if len(args) > 1:
    target_name = args[1]

for vpn_env in env['client_vpn']:
    if target_name and vpn_env['NAME'] != target_name:
        continue

    if region and vpn_env.get('AWS_VPC_REGION') != region:
        continue

    if target_name:
        check_exists = True

    run_terminate_client_vpn(vpn_env['NAME'], vpn_env)

if not check_exists and target_name:
    print(f'{target_name} is not exists in config.json')
