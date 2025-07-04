#!/usr/bin/env python3
import base64
import json
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import write_file

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def get_network_resource_ids(vpc_region):
    service_name = env['common'].get('SERVICE_NAME', '')
    name_prefix = '%s_' % service_name if service_name else ''

    aws_cli = AWSCli(vpc_region)
    cidr_subnet = aws_cli.cidr_subnet

    print_message('get vpc id')

    rds_vpc_id, eb_vpc_id = aws_cli.get_vpc_id()

    if not eb_vpc_id:
        print('ERROR!!! No VPC found')
        raise Exception()

    print_message('get subnet id')

    eb_subnet_id = None
    rds_subnet_id = None
    cmd = ['ec2', 'describe-subnets']
    rr = aws_cli.run(cmd)
    for r in rr['Subnets']:
        if r['VpcId'] not in (eb_vpc_id, rds_vpc_id):
            continue
        if r['CidrBlock'] == cidr_subnet['eb']['private_1']:
            eb_subnet_id = r['SubnetId']
        if r['CidrBlock'] == cidr_subnet['rds']['private_1']:
            rds_subnet_id = r['SubnetId']

    print_message('get security group id')

    eb_security_group_id = None
    cmd = ['ec2', 'describe-security-groups']
    rr = aws_cli.run(cmd)
    for r in rr['SecurityGroups']:
        if r['VpcId'] != eb_vpc_id:
            continue
        if r['GroupName'] == '%seb_private' % name_prefix:
            eb_security_group_id = r['GroupId']
            break

    return eb_vpc_id, rds_vpc_id, eb_subnet_id, rds_subnet_id, eb_security_group_id


def run_create_client_vpn(name, settings):
    vpc_region = settings['AWS_VPC_REGION']
    aws_cli = AWSCli(vpc_region)
    print_message(f'create {name}')

    eb_vpc_id, rds_vpc_id, eb_subnet_id, rds_subnet_id, eb_security_group_id = get_network_resource_ids(vpc_region)

    ################################################################################
    print_message('create SAML identity provider')

    bb = settings['SAML_BASE64']
    bb = bb.encode('ascii')
    bb = base64.decodebytes(bb)
    bb = bb.decode('ascii')

    write_file('/tmp/saml.xml', bb)

    cmd = ['iam', 'create-saml-provider']
    cmd += ['--saml-metadata-document', 'file:///tmp/saml.xml']
    cmd += ['--name', f'AWSClientVPN_SAML_{name}']
    result = aws_cli.run(cmd)

    saml_provider_arn = result['SAMLProviderArn']

    ################################################################################
    print_message('create Self Service Portal SAML identity provider')

    bb = settings['PORTAL_SAML_BASE64']
    bb = bb.encode('ascii')
    bb = base64.decodebytes(bb)
    bb = bb.decode('ascii')

    write_file('/tmp/portal-saml.xml', bb)

    cmd = ['iam', 'create-saml-provider']
    cmd += ['--saml-metadata-document', 'file:///tmp//portal-saml.xml']
    cmd += ['--name', f'AWSClientVPN_Portal_SAML_{name}']
    result = aws_cli.run(cmd)

    portal_saml_provider_arn = result['SAMLProviderArn']

    ################################################################################
    print_message('import server certificate')

    write_file('/tmp/server.crt', settings['SERVER_CRT'])
    write_file('/tmp/server.key', settings['SERVER_KEY'])
    write_file('/tmp/ca.crt', settings['CA_CRT'])

    cmd = ['acm', 'import-certificate']
    cmd += ['--certificate', 'fileb:///tmp/server.crt']
    cmd += ['--private-key', 'fileb:///tmp/server.key']
    cmd += ['--certificate-chain', 'fileb:///tmp/ca.crt']
    result = aws_cli.run(cmd)

    server_cert_arn = result['CertificateArn']

    ################################################################################
    print_message('create log group and stream')

    cmd = ['logs', 'describe-log-groups']
    cmd += ['--log-group-name-prefix', '/aws/ec2/cvpn/connection']
    result = aws_cli.run(cmd)

    if len(result['logGroups']) < 1:
        cmd = ['logs', 'create-log-group']
        cmd += ['--log-group-name', '/aws/ec2/cvpn/connection']
        aws_cli.run(cmd)

    cmd = ['logs', 'describe-log-streams']
    cmd += ['--log-group-name', '/aws/ec2/cvpn/connection']
    cmd += ['--log-stream-name-prefix', f'{name}']
    result = aws_cli.run(cmd)

    if len(result['logStreams']) < 1:
        cmd = ['logs', 'create-log-stream']
        cmd += ['--log-group-name', '/aws/ec2/cvpn/connection']
        cmd += ['--log-stream-name', f'{name}']
        aws_cli.run(cmd)

    ################################################################################
    print_message('create client vpn endpoint')

    ao = dict()
    ao['Type'] = 'federated-authentication'
    ao['FederatedAuthentication'] = dict()
    ao['FederatedAuthentication']['SAMLProviderArn'] = saml_provider_arn
    ao['FederatedAuthentication']['SelfServiceSAMLProviderArn'] = portal_saml_provider_arn
    ao = [ao]

    cmd = ['ec2', 'create-client-vpn-endpoint']
    cmd += ['--client-cidr-block', settings["CLIENT_CIDR_BLOCK"]]
    cmd += ['--server-certificate-arn', server_cert_arn]
    cmd += ['--authentication-options', json.dumps(ao)]
    lo = f'Enabled=true,CloudwatchLogGroup=/aws/ec2/cvpn/connection,CloudwatchLogStream={name}'
    cmd += ['--connection-log-options', lo]
    cmd += ['--vpn-port', '1194']
    cmd += ['--split-tunnel']
    cmd += ['--security-group-ids', eb_security_group_id]
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--tag-specifications', 'ResourceType=client-vpn-endpoint,Tags=[{Key=Name,Value=%s}]' % name]
    cmd += ['--self-service-portal', 'enabled']
    result = aws_cli.run(cmd)

    vpn_endpoint_id = result['ClientVpnEndpointId']

    ################################################################################
    print_message('associate target network')

    cmd = ['ec2', 'associate-client-vpn-target-network']
    cmd += ['--client-vpn-endpoint-id', vpn_endpoint_id]
    cmd += ['--subnet-id', eb_subnet_id]
    aws_cli.run(cmd)

    ################################################################################
    print_message('authorize target network')

    cmd = ['ec2', 'authorize-client-vpn-ingress']
    cmd += ['--client-vpn-endpoint-id', vpn_endpoint_id]
    cmd += ['--target-network-cidr', aws_cli.cidr_vpc['eb']]
    cmd += ['--authorize-all-groups']
    aws_cli.run(cmd)

    cmd = ['ec2', 'authorize-client-vpn-ingress']
    cmd += ['--client-vpn-endpoint-id', vpn_endpoint_id]
    cmd += ['--target-network-cidr', aws_cli.cidr_vpc['rds']]
    cmd += ['--authorize-all-groups']
    aws_cli.run(cmd)

    ################################################################################
    print_message('create route between target network')

    cmd = ['ec2', 'create-client-vpn-route']
    cmd += ['--client-vpn-endpoint-id', vpn_endpoint_id]
    cmd += ['--destination-cidr-block', aws_cli.cidr_vpc['rds']]
    cmd += ['--target-vpc-subnet-id', eb_subnet_id]
    aws_cli.run(cmd)

    elapsed_time = 0
    while True:
        cmd = ['ec2', 'describe-client-vpn-endpoints']
        cmd += ['--client-vpn-endpoint-ids', vpn_endpoint_id]
        result = aws_cli.run(cmd)

        result = result['ClientVpnEndpoints'][0]
        if result['Status']['Code'] == 'available':
            print('endpoint created. download .ovpn from: %s' % result['SelfServicePortalUrl'])
            break

        print('waiting for endpoint available... (elapsed time: \'%d\' seconds)' % elapsed_time)
        time.sleep(5)
        elapsed_time += 5

        if elapsed_time > 60 * 30:
            raise Exception()


################################################################################
#
# start
#
################################################################################
print_session('create client vpn')

################################################################################

target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for vpn_env in env.get('client_vpn', list()):
    if target_name and vpn_env['NAME'] != target_name:
        continue

    if region and vpn_env['AWS_VPC_REGION'] != region:
        continue

    is_target_exists = True

    run_create_client_vpn(vpn_env['NAME'], vpn_env)

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'client vpn: {mm} is not found in config.json')
