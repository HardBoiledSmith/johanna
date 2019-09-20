#!/usr/bin/env python3
import sys

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def main(settings):
    aws_availability_zone_1 = settings['AWS_AVAILABILITY_ZONE_1']
    aws_availability_zone_2 = settings['AWS_AVAILABILITY_ZONE_2']
    aws_cli = AWSCli(settings['AWS_DEFAULT_REGION'])
    rds_subnet_name = env['rds']['DB_SUBNET_NAME']
    service_name = env['common'].get('SERVICE_NAME', '')
    name_prefix = '%s_' % service_name if service_name else ''

    cidr_vpc = aws_cli.cidr_vpc
    cidr_subnet = aws_cli.cidr_subnet

    print_message('get vpc id')

    rds_vpc_id, eb_vpc_id = aws_cli.get_vpc_id()
    if rds_vpc_id or eb_vpc_id:
        print_message('VPC already exists')
        print('RDS: %s \n' % rds_vpc_id)
        print('EB: %s \n' % eb_vpc_id)
        print_session('finish python code')
        sys.exit(0)

    ################################################################################
    #
    # EB Application
    #
    ################################################################################
    print_session('create eb application')

    ################################################################################
    print_message('import key pair')

    cmd = ['ec2', 'import-key-pair']
    cmd += ['--key-name', env['common']['AWS_KEY_PAIR_NAME']]
    cmd += ['--public-key-material', env['common']['AWS_KEY_PAIR_MATERIAL']]
    aws_cli.run(cmd)

    ################################################################################
    print_message('create application')

    eb_service_role_arn = aws_cli.get_iam_role('aws-elasticbeanstalk-service-role')['Role']['Arn']

    config_format = '%s=%s'
    eb_max_count_rule = list()
    eb_max_count_rule.append(config_format % ('DeleteSourceFromS3', 'true'))
    eb_max_count_rule.append(config_format % ('Enabled', 'true'))
    eb_max_count_rule.append(config_format % ('MaxCount', 100))

    cmd = ['elasticbeanstalk', 'create-application']
    cmd += ['--application-name', env['elasticbeanstalk']['APPLICATION_NAME']]
    cmd += ['--resource-lifecycle-config',
            'ServiceRole=%s,VersionLifecycleConfig={MaxCountRule={%s}}' % (
                eb_service_role_arn, ','.join(eb_max_count_rule))]
    aws_cli.run(cmd)

    ################################################################################
    #
    # RDS
    #
    ################################################################################
    print_session('rds')

    ################################################################################
    print_message('create vpc')

    cmd = ['ec2', 'create-vpc']
    cmd += ['--cidr-block', cidr_vpc['rds']]
    result = aws_cli.run(cmd)
    rds_vpc_id = result['Vpc']['VpcId']
    aws_cli.set_name_tag(rds_vpc_id, '%srds' % name_prefix)

    ################################################################################
    print_message('create subnet')

    rds_subnet_id = dict()

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', rds_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['rds']['private_1']]
    cmd += ['--availability-zone', aws_availability_zone_1]
    result = aws_cli.run(cmd)
    rds_subnet_id['private_1'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(rds_subnet_id['private_1'], '%srds_private_1' % name_prefix)

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', rds_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['rds']['private_2']]
    cmd += ['--availability-zone', aws_availability_zone_2]
    result = aws_cli.run(cmd)
    rds_subnet_id['private_2'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(rds_subnet_id['private_2'], '%srds_private_2' % name_prefix)

    ################################################################################
    print_message('create db subnet group')

    cmd = ['rds', 'create-db-subnet-group']
    cmd += ['--db-subnet-group-name', rds_subnet_name]
    cmd += ['--db-subnet-group-description', rds_subnet_name]
    cmd += ['--subnet-ids', rds_subnet_id['private_1'], rds_subnet_id['private_2']]
    aws_cli.run(cmd)

    ################################################################################
    print_message('create ' + 'route table')  # [FYI] PyCharm inspects 'create route table' as SQL query.

    rds_route_table_id = dict()

    cmd = ['ec2', 'create-route-table']
    cmd += ['--vpc-id', rds_vpc_id]
    result = aws_cli.run(cmd)
    rds_route_table_id['private'] = result['RouteTable']['RouteTableId']
    aws_cli.set_name_tag(rds_route_table_id['private'], '%srds_private' % name_prefix)

    ################################################################################
    print_message('associate route table')

    cmd = ['ec2', 'associate-route-table']
    cmd += ['--subnet-id', rds_subnet_id['private_1']]
    cmd += ['--route-table-id', rds_route_table_id['private']]
    aws_cli.run(cmd)

    cmd = ['ec2', 'associate-route-table']
    cmd += ['--subnet-id', rds_subnet_id['private_2']]
    cmd += ['--route-table-id', rds_route_table_id['private']]
    aws_cli.run(cmd)

    ################################################################################
    print_message('create security group')

    rds_security_group_id = dict()

    cmd = ['ec2', 'create-security-group']
    cmd += ['--group-name', '%srds' % name_prefix]
    cmd += ['--description', '%srds' % name_prefix]
    cmd += ['--vpc-id', rds_vpc_id]
    result = aws_cli.run(cmd)
    rds_security_group_id['private'] = result['GroupId']

    ################################################################################
    print_message('authorize security group ingress')

    cmd = ['ec2', 'authorize-security-group-ingress']
    cmd += ['--group-id', rds_security_group_id['private']]
    cmd += ['--protocol', 'all']
    cmd += ['--source-group', rds_security_group_id['private']]
    aws_cli.run(cmd)

    cmd = ['ec2', 'authorize-security-group-ingress']
    cmd += ['--group-id', rds_security_group_id['private']]
    cmd += ['--protocol', 'tcp']
    cmd += ['--port', '3306']
    cmd += ['--cidr', cidr_vpc['eb']]
    aws_cli.run(cmd)

    ################################################################################
    #
    # EB
    #
    ################################################################################
    print_session('eb')

    ################################################################################
    print_message('create vpc')

    cmd = ['ec2', 'create-vpc']
    cmd += ['--cidr-block', cidr_vpc['eb']]
    result = aws_cli.run(cmd)
    eb_vpc_id = result['Vpc']['VpcId']
    aws_cli.set_name_tag(eb_vpc_id, '%seb' % name_prefix)

    ################################################################################
    print_message('create subnet')

    eb_subnet_id = dict()

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['eb']['private_1']]
    cmd += ['--availability-zone', aws_availability_zone_1]
    result = aws_cli.run(cmd)
    eb_subnet_id['private_1'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(eb_subnet_id['private_1'], '%seb_private_1' % name_prefix)

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['eb']['private_2']]
    cmd += ['--availability-zone', aws_availability_zone_2]
    result = aws_cli.run(cmd)
    eb_subnet_id['private_2'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(eb_subnet_id['private_2'], '%seb_private_2' % name_prefix)

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['eb']['public_1']]
    cmd += ['--availability-zone', aws_availability_zone_1]
    result = aws_cli.run(cmd)
    eb_subnet_id['public_1'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(eb_subnet_id['public_1'], '%seb_public_1' % name_prefix)

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['eb']['public_2']]
    cmd += ['--availability-zone', aws_availability_zone_2]
    result = aws_cli.run(cmd)
    eb_subnet_id['public_2'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(eb_subnet_id['public_2'], '%seb_public_2' % name_prefix)

    ################################################################################
    print_message('create internet gateway')

    cmd = ['ec2', 'create-internet-gateway']
    result = aws_cli.run(cmd)
    internet_gateway_id = result['InternetGateway']['InternetGatewayId']
    aws_cli.set_name_tag(internet_gateway_id, '%seb' % name_prefix)

    ################################################################################
    print_message('attach internet gateway')

    cmd = ['ec2', 'attach-internet-gateway']
    cmd += ['--internet-gateway-id', internet_gateway_id]
    cmd += ['--vpc-id', eb_vpc_id]
    aws_cli.run(cmd)

    ################################################################################
    print_message('create eip')  # We use only one NAT gateway at subnet 'public_1'

    cmd = ['ec2', 'allocate-address']
    cmd += ['--domain', 'vpc']
    result = aws_cli.run(cmd)
    eb_eip_id = result['AllocationId']
    aws_cli.set_name_tag(eb_eip_id, '%snat' % name_prefix)

    ################################################################################
    print_message('create nat gateway')  # We use only one NAT gateway at subnet 'public_1'

    cmd = ['ec2', 'create-nat-gateway']
    cmd += ['--subnet-id', eb_subnet_id['public_1']]
    cmd += ['--allocation-id', eb_eip_id]
    result = aws_cli.run(cmd)
    eb_nat_gateway_id = result['NatGateway']['NatGatewayId']
    aws_cli.set_name_tag(eb_nat_gateway_id, '%seb' % name_prefix)

    ################################################################################
    print_message('wait create nat gateway')

    aws_cli.wait_create_nat_gateway(eb_vpc_id)

    ################################################################################
    print_message('create ' + 'route table')  # [FYI] PyCharm inspects 'create route table' as SQL query.

    eb_route_table_id = dict()

    cmd = ['ec2', 'create-route-table']
    cmd += ['--vpc-id', eb_vpc_id]
    result = aws_cli.run(cmd)
    eb_route_table_id['private'] = result['RouteTable']['RouteTableId']
    aws_cli.set_name_tag(eb_route_table_id['private'], '%seb_private' % name_prefix)

    cmd = ['ec2', 'create-route-table']
    cmd += ['--vpc-id', eb_vpc_id]
    result = aws_cli.run(cmd)
    eb_route_table_id['public'] = result['RouteTable']['RouteTableId']
    aws_cli.set_name_tag(eb_route_table_id['public'], '%seb_public' % name_prefix)

    ################################################################################
    print_message('associate route table')

    cmd = ['ec2', 'associate-route-table']
    cmd += ['--subnet-id', eb_subnet_id['private_1']]
    cmd += ['--route-table-id', eb_route_table_id['private']]
    aws_cli.run(cmd)

    cmd = ['ec2', 'associate-route-table']
    cmd += ['--subnet-id', eb_subnet_id['private_2']]
    cmd += ['--route-table-id', eb_route_table_id['private']]
    aws_cli.run(cmd)

    cmd = ['ec2', 'associate-route-table']
    cmd += ['--subnet-id', eb_subnet_id['public_1']]
    cmd += ['--route-table-id', eb_route_table_id['public']]
    aws_cli.run(cmd)

    cmd = ['ec2', 'associate-route-table']
    cmd += ['--subnet-id', eb_subnet_id['public_2']]
    cmd += ['--route-table-id', eb_route_table_id['public']]
    aws_cli.run(cmd)

    ################################################################################
    print_message('create route')

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', eb_route_table_id['public']]
    cmd += ['--destination-cidr-block', '0.0.0.0/0']
    cmd += ['--gateway-id', internet_gateway_id]
    aws_cli.run(cmd)

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', eb_route_table_id['private']]
    cmd += ['--destination-cidr-block', '0.0.0.0/0']
    cmd += ['--nat-gateway-id', eb_nat_gateway_id]
    aws_cli.run(cmd)

    ################################################################################
    print_message('create security group')

    eb_security_group_id = dict()

    cmd = ['ec2', 'create-security-group']
    cmd += ['--group-name', '%seb_private' % name_prefix]
    cmd += ['--description', '%seb_private' % name_prefix]
    cmd += ['--vpc-id', eb_vpc_id]
    result = aws_cli.run(cmd)
    eb_security_group_id['private'] = result['GroupId']

    cmd = ['ec2', 'create-security-group']
    cmd += ['--group-name', '%seb_public' % name_prefix]
    cmd += ['--description', '%seb_public' % name_prefix]
    cmd += ['--vpc-id', eb_vpc_id]
    result = aws_cli.run(cmd)
    eb_security_group_id['public'] = result['GroupId']

    ################################################################################
    print_message('authorize security group ingress')

    cmd = ['ec2', 'authorize-security-group-ingress']
    cmd += ['--group-id', eb_security_group_id['private']]
    cmd += ['--protocol', 'all']
    cmd += ['--source-group', eb_security_group_id['private']]
    aws_cli.run(cmd)

    cmd = ['ec2', 'authorize-security-group-ingress']
    cmd += ['--group-id', eb_security_group_id['private']]
    cmd += ['--protocol', 'all']
    cmd += ['--source-group', eb_security_group_id['public']]
    aws_cli.run(cmd)

    cmd = ['ec2', 'authorize-security-group-ingress']
    cmd += ['--group-id', eb_security_group_id['public']]
    cmd += ['--protocol', 'all']
    cmd += ['--source-group', eb_security_group_id['private']]
    aws_cli.run(cmd)

    cmd = ['ec2', 'authorize-security-group-ingress']
    cmd += ['--group-id', eb_security_group_id['public']]
    cmd += ['--protocol', 'all']
    cmd += ['--source-group', eb_security_group_id['public']]
    aws_cli.run(cmd)

    cmd = ['ec2', 'authorize-security-group-ingress']
    cmd += ['--group-id', eb_security_group_id['public']]
    cmd += ['--protocol', 'tcp']
    cmd += ['--port', '22']
    cmd += ['--cidr', cidr_vpc['eb']]
    aws_cli.run(cmd)

    cmd = ['ec2', 'authorize-security-group-ingress']
    cmd += ['--group-id', eb_security_group_id['public']]
    cmd += ['--protocol', 'tcp']
    cmd += ['--port', '80']
    cmd += ['--cidr', '0.0.0.0/0']
    aws_cli.run(cmd)

    ################################################################################
    #
    # ElastiCache
    #
    ################################################################################
    print_session('elasticache')

    ################################################################################
    if env.get('elasticache'):
        elasticache_subnet_name = env['elasticache']['CACHE_SUBNET_NAME']

        print_message('create cache subnet group')

        cmd = ['elasticache', 'create-cache-subnet-group']
        cmd += ['--cache-subnet-group-name', elasticache_subnet_name]
        cmd += ['--cache-subnet-group-description', elasticache_subnet_name]
        cmd += ['--subnet-ids', eb_subnet_id['private_1'], eb_subnet_id['private_2']]
        aws_cli.run(cmd)

    ################################################################################
    #
    # vpc peering connection
    #
    ################################################################################
    print_session('vpc peering connection')

    ################################################################################
    print_message('create vpc peering connection')

    cmd = ['ec2', 'create-vpc-peering-connection']
    cmd += ['--vpc-id', rds_vpc_id]
    cmd += ['--peer-vpc-id', eb_vpc_id]
    result = aws_cli.run(cmd)
    peering_connection_id = result['VpcPeeringConnection']['VpcPeeringConnectionId']
    aws_cli.set_name_tag(peering_connection_id, '%s' % service_name)

    cmd = ['ec2', 'accept-vpc-peering-connection']
    cmd += ['--vpc-peering-connection-id', peering_connection_id]
    aws_cli.run(cmd)

    ################################################################################
    print_message('create route: rds -> eb')

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', rds_route_table_id['private']]
    cmd += ['--destination-cidr-block', cidr_subnet['eb']['private_1']]
    cmd += ['--vpc-peering-connection-id', peering_connection_id]
    aws_cli.run(cmd)

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', rds_route_table_id['private']]
    cmd += ['--destination-cidr-block', cidr_subnet['eb']['private_2']]
    cmd += ['--vpc-peering-connection-id', peering_connection_id]
    aws_cli.run(cmd)

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', rds_route_table_id['private']]
    cmd += ['--destination-cidr-block', cidr_subnet['eb']['public_1']]
    cmd += ['--vpc-peering-connection-id', peering_connection_id]
    aws_cli.run(cmd)

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', rds_route_table_id['private']]
    cmd += ['--destination-cidr-block', cidr_subnet['eb']['public_2']]
    cmd += ['--vpc-peering-connection-id', peering_connection_id]
    aws_cli.run(cmd)

    ################################################################################
    print_message('create route: eb -> rds')

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', eb_route_table_id['private']]
    cmd += ['--destination-cidr-block', cidr_subnet['rds']['private_1']]
    cmd += ['--vpc-peering-connection-id', peering_connection_id]
    aws_cli.run(cmd)

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', eb_route_table_id['private']]
    cmd += ['--destination-cidr-block', cidr_subnet['rds']['private_2']]
    cmd += ['--vpc-peering-connection-id', peering_connection_id]
    aws_cli.run(cmd)

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', eb_route_table_id['public']]
    cmd += ['--destination-cidr-block', cidr_subnet['rds']['private_1']]
    cmd += ['--vpc-peering-connection-id', peering_connection_id]
    aws_cli.run(cmd)

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', eb_route_table_id['public']]
    cmd += ['--destination-cidr-block', cidr_subnet['rds']['private_2']]
    cmd += ['--vpc-peering-connection-id', peering_connection_id]
    aws_cli.run(cmd)

    ################################################################################
    #
    # Network Interface
    #
    ################################################################################
    print_session('network interface')

    ################################################################################
    environment_list = env['elasticbeanstalk']['ENVIRONMENTS']
    for environment in environment_list:
        cname = environment['CNAME']
        private_ip = environment.get('PRIVATE_IP')

        if cname and private_ip:
            print_message('create network interface for %s' % cname)

            cmd = ['ec2', 'create-network-interface']
            cmd += ['--subnet-id', eb_subnet_id['private_1']]
            cmd += ['--description', cname]
            cmd += ['--private-ip-address', private_ip]
            cmd += ['--groups', eb_security_group_id['private']]
            result = aws_cli.run(cmd)
            network_interface_id = result['NetworkInterface']['NetworkInterfaceId']
            aws_cli.set_name_tag(network_interface_id, '%snat' % name_prefix)


################################################################################
#
# start
#
################################################################################
print_session('create vpc')

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
