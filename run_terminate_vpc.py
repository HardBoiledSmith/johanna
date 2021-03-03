#!/usr/bin/env python3
from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def main(settings):
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])
    rds_subnet_name = env['rds']['DB_SUBNET_NAME']
    service_name = env['common'].get('SERVICE_NAME', '')
    name_prefix = '%s_' % service_name if service_name else ''

    ################################################################################
    print_message('wait terminate rds')

    aws_cli.wait_terminate_rds()

    ################################################################################
    print_message('wait terminate elasticache')

    aws_cli.wait_terminate_elasticache()

    ################################################################################
    print_message('wait terminate eb')

    aws_cli.wait_terminate_eb()

    ################################################################################
    print_message('get vpc id')

    rds_vpc_id, eb_vpc_id = aws_cli.get_vpc_id()

    ################################################################################
    print_message('delete network interface')

    cmd = ['ec2', 'describe-network-interfaces']
    result = aws_cli.run(cmd, ignore_error=True)

    for r in result['NetworkInterfaces']:
        if r['VpcId'] != rds_vpc_id and r['VpcId'] != eb_vpc_id:
            continue
        network_interface_id = r['NetworkInterfaceId']

        if 'Attachment' in r:
            attachment_id = r['Attachment']['AttachmentId']

            cmd = ['ec2', 'detach-network-interface']
            cmd += ['--attachment-id', attachment_id]
            aws_cli.run(cmd, ignore_error=True)

        cmd = ['ec2', 'delete-network-interface']
        cmd += ['--network-interface-id', network_interface_id]
        aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete vpc peering connection')

    cmd = ['ec2', 'describe-vpc-peering-connections']
    result = aws_cli.run(cmd, ignore_error=True)
    for vpc_peer in result['VpcPeeringConnections']:
        if vpc_peer['RequesterVpcInfo']['VpcId'] == rds_vpc_id and vpc_peer['AccepterVpcInfo']['VpcId'] == eb_vpc_id:
            peering_connection_id = vpc_peer['VpcPeeringConnectionId']
            print('delete vpc peering connnection (id: %s)' % peering_connection_id)
            cmd = ['ec2', 'delete-vpc-peering-connection']
            cmd += ['--vpc-peering-connection-id', peering_connection_id]
            aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('revoke security group ingress')

    security_group_id_1 = None
    security_group_id_2 = None
    cmd = ['ec2', 'describe-security-groups']
    result = aws_cli.run(cmd, ignore_error=True)
    for r in result['SecurityGroups']:
        if r['VpcId'] != rds_vpc_id and r['VpcId'] != eb_vpc_id:
            continue
        if r['GroupName'] == '%seb_private' % name_prefix:
            security_group_id_1 = r['GroupId']
        if r['GroupName'] == '%seb_public' % name_prefix:
            security_group_id_2 = r['GroupId']

    if security_group_id_1 and security_group_id_2:
        cmd = ['ec2', 'revoke-security-group-ingress']
        cmd += ['--group-id', security_group_id_1]
        cmd += ['--protocol', 'all']
        cmd += ['--source-group', security_group_id_2]
        aws_cli.run(cmd, ignore_error=True)

        cmd = ['ec2', 'revoke-security-group-ingress']
        cmd += ['--group-id', security_group_id_2]
        cmd += ['--protocol', 'all']
        cmd += ['--source-group', security_group_id_1]
        aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete security group')

    cmd = ['ec2', 'describe-security-groups']
    result = aws_cli.run(cmd, ignore_error=True)
    for r in result['SecurityGroups']:
        if r['VpcId'] != rds_vpc_id and r['VpcId'] != eb_vpc_id:
            continue
        if r['GroupName'] == 'default':
            continue
        print('delete security group (id: %s)' % r['GroupId'])
        cmd = ['ec2', 'delete-security-group']
        cmd += ['--group-id', r['GroupId']]
        aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete route')

    cmd = ['ec2', 'describe-route-tables']
    result = aws_cli.run(cmd, ignore_error=True)
    for r in result['RouteTables']:
        if r['VpcId'] != rds_vpc_id and r['VpcId'] != eb_vpc_id:
            continue
        for route in r['Routes']:
            if route['DestinationCidrBlock'] == '0.0.0.0/0':
                print('delete route (route table id: %s)' % r['RouteTableId'])
                cmd = ['ec2', 'delete-route']
                cmd += ['--route-table-id', r['RouteTableId']]
                cmd += ['--destination-cidr-block', '0.0.0.0/0']
                aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('disassociate route table')

    cmd = ['ec2', 'describe-route-tables']
    result = aws_cli.run(cmd, ignore_error=True)
    for r in result['RouteTables']:
        if r['VpcId'] != rds_vpc_id and r['VpcId'] != eb_vpc_id:
            continue
        for association in r['Associations']:
            if association['Main']:
                continue
            print('disassociate route table (route table id: %s, route table association id: %s)' %
                  (r['RouteTableId'], association['RouteTableAssociationId']))
            cmd = ['ec2', 'disassociate-route-table']
            cmd += ['--association-id', association['RouteTableAssociationId']]
            aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete route table')

    cmd = ['ec2', 'describe-route-tables']
    result = aws_cli.run(cmd, ignore_error=True)
    for r in result['RouteTables']:
        if r['VpcId'] != rds_vpc_id and r['VpcId'] != eb_vpc_id:
            continue
        if len(r['Associations']) != 0:
            continue
        print('delete route table (route table id: %s)' % r['RouteTableId'])
        cmd = ['ec2', 'delete-route-table']
        cmd += ['--route-table-id', r['RouteTableId']]
        aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete nat gateway')

    cmd = ['ec2', 'describe-nat-gateways']
    result = aws_cli.run(cmd, ignore_error=True)
    for r in result['NatGateways']:
        if r['VpcId'] != rds_vpc_id and r['VpcId'] != eb_vpc_id:
            continue
        print('delete nat gateway (nat gateway id: %s)' % r['NatGatewayId'])
        cmd = ['ec2', 'delete-nat-gateway']
        cmd += ['--nat-gateway-id', r['NatGatewayId']]
        aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('wait delete nat gateway')

    aws_cli.wait_delete_nat_gateway(eb_vpc_id=eb_vpc_id)

    ################################################################################
    print_message('release eip')

    cmd = ['ec2', 'describe-addresses']
    result = aws_cli.run(cmd, ignore_error=True)
    for r in result['Addresses']:
        if 'AssociationId' in r:
            continue
        print('release address (address id: %s)' % r['AllocationId'])
        cmd = ['ec2', 'release-address']
        cmd += ['--allocation-id', r['AllocationId']]
        aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    if env.get('elasticache'):
        elasticache_subnet_name = env['elasticache']['CACHE_SUBNET_NAME']

        print_message('delete cache subnet group')

        cmd = ['elasticache', 'delete-cache-subnet-group']
        cmd += ['--cache-subnet-group-name', elasticache_subnet_name]
        aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete db subnet group')

    cmd = ['rds', 'delete-db-subnet-group']
    cmd += ['--db-subnet-group-name', rds_subnet_name]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('detach internet gateway')

    cmd = ['ec2', 'describe-internet-gateways']
    result = aws_cli.run(cmd, ignore_error=True)
    for r in result['InternetGateways']:
        if len(r['Attachments']) != 1:
            continue
        if r['Attachments'][0]['VpcId'] != eb_vpc_id:
            continue
        print('detach internet gateway (internet gateway id: %s)' % r['InternetGatewayId'])
        cmd = ['ec2', 'detach-internet-gateway']
        cmd += ['--internet-gateway-id', r['InternetGatewayId']]
        cmd += ['--vpc-id', r['Attachments'][0]['VpcId']]
        aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete internet gateway')

    cmd = ['ec2', 'describe-internet-gateways']
    result = aws_cli.run(cmd, ignore_error=True)
    for r in result['InternetGateways']:
        if len(r['Attachments']) != 0:
            continue
        print('delete internet gateway (internet gateway id: %s)' % r['InternetGatewayId'])
        cmd = ['ec2', 'delete-internet-gateway']
        cmd += ['--internet-gateway-id', r['InternetGatewayId']]
        aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete subnet')

    cmd = ['ec2', 'describe-subnets']
    result = aws_cli.run(cmd, ignore_error=True)
    for r in result['Subnets']:
        if r['VpcId'] != rds_vpc_id and r['VpcId'] != eb_vpc_id:
            continue
        print('delete subnet (subnet id: %s)' % r['SubnetId'])
        cmd = ['ec2', 'delete-subnet']
        cmd += ['--subnet-id', r['SubnetId']]
        aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete vpc')

    while rds_vpc_id or eb_vpc_id:
        if rds_vpc_id:
            print('delete vpc (vpc id: %s)' % rds_vpc_id)
            cmd = ['ec2', 'delete-vpc']
            cmd += ['--vpc-id', rds_vpc_id]
            aws_cli.run(cmd, ignore_error=True)

        if eb_vpc_id:
            print('delete vpc (vpc id: %s)' % eb_vpc_id)
            cmd = ['ec2', 'delete-vpc']
            cmd += ['--vpc-id', eb_vpc_id]
            aws_cli.run(cmd, ignore_error=True)

        rds_vpc_id, eb_vpc_id = aws_cli.get_vpc_id()

    ################################################################################
    #
    # EB Application
    #
    ################################################################################
    print_session('terminate eb application')

    ################################################################################
    print_message('delete application')

    cmd = ['elasticbeanstalk', 'delete-application']
    cmd += ['--application-name', env['elasticbeanstalk']['APPLICATION_NAME']]
    aws_cli.run(cmd, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate vpc')

region = None
check_exists = False

if len(args) > 1:
    region = args[1]

for vpc_env in env['vpc']:

    if region and vpc_env.get('AWS_DEFAULT_REGION') != region:
        continue

    check_exists = True

    main(vpc_env)

if not check_exists and region:
    print('vpc for "%s" is not exists in config.json' % region)
