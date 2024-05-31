#!/usr/bin/env python3
import sys

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def main(settings):
    aws_availability_zone_1 = settings['AWS_AVAILABILITY_ZONE_1']
    aws_availability_zone_2 = settings['AWS_AVAILABILITY_ZONE_2']
    aws_availability_zone_3 = settings['AWS_AVAILABILITY_ZONE_3']
    aws_availability_zone_4 = settings['AWS_AVAILABILITY_ZONE_4']
    aws_cli = AWSCli(settings['AWS_REGION'])
    rds_subnet_name = env['rds']['DB_SUBNET_NAME']

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
    print_message('create service role')

    cmd = ['iam', 'create-role']
    cmd += ['--role-name', 'aws-elasticbeanstalk-service-role']
    cmd += ['--assume-role-policy-document', 'file://aws_iam/aws-elasticbeanstalk-service-role.json']
    aws_cli.run(cmd)

    cmd = ['iam', 'attach-role-policy']
    cmd += ['--role-name', 'aws-elasticbeanstalk-service-role']
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalkEnhancedHealth']
    aws_cli.run(cmd)

    cmd = ['iam', 'attach-role-policy']
    cmd += ['--role-name', 'aws-elasticbeanstalk-service-role']
    cmd += ['--policy-arn', 'arn:aws:iam::aws:policy/AWSElasticBeanstalkManagedUpdatesCustomerRolePolicy']
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
    # Default
    #
    ################################################################################

    cmd = ['ec2', 'describe-vpcs']
    cmd += ['--filters', 'Name=isDefault,Values=true']
    cmd += ['--query', 'Vpcs[0].VpcId']
    default_vpc_id = aws_cli.run(cmd)

    cmd = ['ec2', 'describe-security-groups']
    cmd += ['--filters', f'Name=vpc-id,Values={default_vpc_id}', "Name=group-name,Values=default"]
    cmd += ['--query', 'SecurityGroups[0].GroupId']
    default_security_group_id = aws_cli.run(cmd)

    cmd = ['ec2', 'describe-security-group-rules']
    cmd += ['--filters', f'Name=group-id,Values={default_security_group_id}']
    cmd += ['--query', 'SecurityGroupRules[*].{SecurityGroupRuleId:SecurityGroupRuleId, IsEgress:IsEgress}']
    result = aws_cli.run(cmd)

    ingress_rule_ids = [x['SecurityGroupRuleId'] for x in result if not x['IsEgress']]
    if ingress_rule_ids:
        cmd = ['ec2', 'revoke-security-group-ingress']
        cmd += ['--group-id', default_security_group_id]
        cmd += ['--security-group-rule-ids'] + ingress_rule_ids
        aws_cli.run(cmd)

    egress_rule_ids = [x['SecurityGroupRuleId'] for x in result if x['IsEgress']]
    if egress_rule_ids:
        cmd = ['ec2', 'revoke-security-group-egress']
        cmd += ['--group-id', default_security_group_id]
        cmd += ['--security-group-rule-ids'] + egress_rule_ids
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
    aws_cli.set_name_tag(rds_vpc_id, 'rds')

    ################################################################################
    print_message('create subnet')

    rds_subnet_id = dict()

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', rds_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['rds']['private_1']]
    cmd += ['--availability-zone', aws_availability_zone_1]
    result = aws_cli.run(cmd)
    rds_subnet_id['private_1'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(rds_subnet_id['private_1'], 'rds_private_1')

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', rds_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['rds']['private_2']]
    cmd += ['--availability-zone', aws_availability_zone_2]
    result = aws_cli.run(cmd)
    rds_subnet_id['private_2'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(rds_subnet_id['private_2'], 'rds_private_2')

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', rds_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['rds']['private_3']]
    cmd += ['--availability-zone', aws_availability_zone_3]
    result = aws_cli.run(cmd)
    rds_subnet_id['private_3'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(rds_subnet_id['private_3'], 'rds_private_3')

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', rds_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['rds']['private_4']]
    cmd += ['--availability-zone', aws_availability_zone_4]
    result = aws_cli.run(cmd)
    rds_subnet_id['private_4'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(rds_subnet_id['private_4'], 'rds_private_4')

    ################################################################################
    print_message('create db subnet group')

    cmd = ['rds', 'create-db-subnet-group']
    cmd += ['--db-subnet-group-name', rds_subnet_name]
    cmd += ['--db-subnet-group-description', rds_subnet_name]
    cmd += ['--subnet-ids', rds_subnet_id['private_1'], rds_subnet_id['private_2'], rds_subnet_id['private_3'],
            rds_subnet_id['private_4']]
    aws_cli.run(cmd)

    ################################################################################
    print_message('create ' + 'route table')  # [FYI] PyCharm inspects 'create route table' as SQL query.

    rds_route_table_id = dict()

    cmd = ['ec2', 'create-route-table']
    cmd += ['--vpc-id', rds_vpc_id]
    result = aws_cli.run(cmd)
    rds_route_table_id['private'] = result['RouteTable']['RouteTableId']
    aws_cli.set_name_tag(rds_route_table_id['private'], 'rds_private')

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

    cmd = ['ec2', 'associate-route-table']
    cmd += ['--subnet-id', rds_subnet_id['private_3']]
    cmd += ['--route-table-id', rds_route_table_id['private']]
    aws_cli.run(cmd)

    cmd = ['ec2', 'associate-route-table']
    cmd += ['--subnet-id', rds_subnet_id['private_4']]
    cmd += ['--route-table-id', rds_route_table_id['private']]
    aws_cli.run(cmd)
    ################################################################################
    print_message('create security group')

    rds_security_group_id = dict()

    cmd = ['ec2', 'create-security-group']
    cmd += ['--group-name', 'rds']
    cmd += ['--description', 'rds']
    cmd += ['--vpc-id', rds_vpc_id]
    result = aws_cli.run(cmd)
    rds_security_group_id['private'] = result['GroupId']

    cmd = ['ec2', 'describe-security-groups']
    cmd += ['--filters', f'Name=vpc-id,Values={rds_vpc_id}']
    result = aws_cli.run(cmd)
    for sg in result['SecurityGroups']:
        if sg['GroupName'] != 'default':
            continue
        rds_security_group_id['default'] = sg['GroupId']

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

    cmd = ['ec2', 'describe-security-group-rules']
    cmd += ['--filters', f'Name=group-id,Values={rds_security_group_id["default"]}']
    cmd += ['--query', 'SecurityGroupRules[*].{SecurityGroupRuleId:SecurityGroupRuleId, IsEgress:IsEgress}']
    result = aws_cli.run(cmd)

    ingress_rule_ids = [x['SecurityGroupRuleId'] for x in result if not x['IsEgress']]
    if ingress_rule_ids:
        cmd = ['ec2', 'revoke-security-group-ingress']
        cmd += ['--group-id', rds_security_group_id['default']]
        cmd += ['--security-group-rule-ids'] + ingress_rule_ids
        aws_cli.run(cmd)

    egress_rule_ids = [x['SecurityGroupRuleId'] for x in result if x['IsEgress']]
    if egress_rule_ids:
        cmd = ['ec2', 'revoke-security-group-egress']
        cmd += ['--group-id', rds_security_group_id['default']]
        cmd += ['--security-group-rule-ids'] + egress_rule_ids
        aws_cli.run(cmd)

    ################################################################################
    print_message('create network acl')

    cmd = ['ec2', 'describe-network-acls']
    cmd += ['--filters', f'Name=vpc-id,Values={rds_vpc_id}']
    cmd += ['--query', 'NetworkAcls[*].{NetworkAclId:NetworkAclId, IsDefault:IsDefault, Entries:Entries}']
    rr = aws_cli.run(cmd)
    rr = rr[0]
    rds_network_acl_id = rr['NetworkAclId']

    cmd = ['ec2', 'create-network-acl-entry']
    cmd += ['--network-acl-id', rds_network_acl_id]
    cmd += ['--rule-number', '10']
    cmd += ['--protocol', 'tcp']
    cmd += ['--port-range', 'From=22,To=22']
    cmd += ['--ingress']
    cmd += ['--rule-action', 'deny']
    cmd += ['--cidr-block', '0.0.0.0/0']
    aws_cli.run(cmd)

    cmd = ['ec2', 'create-network-acl-entry']
    cmd += ['--network-acl-id', rds_network_acl_id]
    cmd += ['--rule-number', '20']
    cmd += ['--protocol', 'tcp']
    cmd += ['--port-range', 'From=3386,To=3386']
    cmd += ['--ingress']
    cmd += ['--rule-action', 'deny']
    cmd += ['--cidr-block', '0.0.0.0/0']
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
    aws_cli.set_name_tag(eb_vpc_id, 'eb')

    ################################################################################
    print_message('create subnet')

    eb_subnet_id = dict()

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['eb']['private_1']]
    cmd += ['--availability-zone', aws_availability_zone_1]
    result = aws_cli.run(cmd)
    eb_subnet_id['private_1'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(eb_subnet_id['private_1'], 'eb_private_1')

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['eb']['private_2']]
    cmd += ['--availability-zone', aws_availability_zone_2]
    result = aws_cli.run(cmd)
    eb_subnet_id['private_2'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(eb_subnet_id['private_2'], 'eb_private_2')

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['eb']['private_3']]
    cmd += ['--availability-zone', aws_availability_zone_3]
    result = aws_cli.run(cmd)
    eb_subnet_id['private_3'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(eb_subnet_id['private_3'], 'eb_private_3')

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['eb']['private_4']]
    cmd += ['--availability-zone', aws_availability_zone_4]
    result = aws_cli.run(cmd)
    eb_subnet_id['private_4'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(eb_subnet_id['private_4'], 'eb_private_4')

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['eb']['public_1']]
    cmd += ['--availability-zone', aws_availability_zone_1]
    result = aws_cli.run(cmd)
    eb_subnet_id['public_1'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(eb_subnet_id['public_1'], 'eb_public_1')

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['eb']['public_2']]
    cmd += ['--availability-zone', aws_availability_zone_2]
    result = aws_cli.run(cmd)
    eb_subnet_id['public_2'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(eb_subnet_id['public_2'], 'eb_public_2')

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['eb']['public_3']]
    cmd += ['--availability-zone', aws_availability_zone_3]
    result = aws_cli.run(cmd)
    eb_subnet_id['public_3'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(eb_subnet_id['public_3'], 'eb_public_3')

    cmd = ['ec2', 'create-subnet']
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--cidr-block', cidr_subnet['eb']['public_4']]
    cmd += ['--availability-zone', aws_availability_zone_4]
    result = aws_cli.run(cmd)
    eb_subnet_id['public_4'] = result['Subnet']['SubnetId']
    aws_cli.set_name_tag(eb_subnet_id['public_4'], 'eb_public_4')

    ################################################################################
    print_message('create internet gateway')

    cmd = ['ec2', 'create-internet-gateway']
    result = aws_cli.run(cmd)
    internet_gateway_id = result['InternetGateway']['InternetGatewayId']
    aws_cli.set_name_tag(internet_gateway_id, 'eb')

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
    aws_cli.set_name_tag(eb_eip_id, 'nat')

    ################################################################################
    print_message('create nat gateway')  # We use only one NAT gateway at subnet 'public_1'

    cmd = ['ec2', 'create-nat-gateway']
    cmd += ['--subnet-id', eb_subnet_id['public_1']]
    cmd += ['--allocation-id', eb_eip_id]
    result = aws_cli.run(cmd)
    eb_nat_gateway_id = result['NatGateway']['NatGatewayId']
    aws_cli.set_name_tag(eb_nat_gateway_id, 'eb')

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
    aws_cli.set_name_tag(eb_route_table_id['private'], 'eb_private')

    cmd = ['ec2', 'create-route-table']
    cmd += ['--vpc-id', eb_vpc_id]
    result = aws_cli.run(cmd)
    eb_route_table_id['public'] = result['RouteTable']['RouteTableId']
    aws_cli.set_name_tag(eb_route_table_id['public'], 'eb_public')

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
    cmd += ['--subnet-id', eb_subnet_id['private_3']]
    cmd += ['--route-table-id', eb_route_table_id['private']]
    aws_cli.run(cmd)

    cmd = ['ec2', 'associate-route-table']
    cmd += ['--subnet-id', eb_subnet_id['private_4']]
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

    cmd = ['ec2', 'associate-route-table']
    cmd += ['--subnet-id', eb_subnet_id['public_3']]
    cmd += ['--route-table-id', eb_route_table_id['public']]
    aws_cli.run(cmd)

    cmd = ['ec2', 'associate-route-table']
    cmd += ['--subnet-id', eb_subnet_id['public_4']]
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
    cmd += ['--group-name', 'eb_private']
    cmd += ['--description', 'eb_private']
    cmd += ['--vpc-id', eb_vpc_id]
    result = aws_cli.run(cmd)
    eb_security_group_id['private'] = result['GroupId']

    cmd = ['ec2', 'create-security-group']
    cmd += ['--group-name', 'eb_public']
    cmd += ['--description', 'eb_public']
    cmd += ['--vpc-id', eb_vpc_id]
    result = aws_cli.run(cmd)
    eb_security_group_id['public'] = result['GroupId']

    cmd = ['ec2', 'describe-security-groups']
    cmd += ['--filters', f'Name=vpc-id,Values={eb_vpc_id}']
    result = aws_cli.run(cmd)
    for sg in result['SecurityGroups']:
        if sg['GroupName'] != 'default':
            continue
        eb_security_group_id['default'] = sg['GroupId']

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
    cmd += ['--port', '80']
    cmd += ['--cidr', '0.0.0.0/0']
    aws_cli.run(cmd)

    cmd = ['ec2', 'describe-security-group-rules']
    cmd += ['--filters', f'Name=group-id,Values={eb_security_group_id["default"]}']
    cmd += ['--query', 'SecurityGroupRules[*].{SecurityGroupRuleId:SecurityGroupRuleId, IsEgress:IsEgress}']
    result = aws_cli.run(cmd)

    ingress_rule_ids = [x['SecurityGroupRuleId'] for x in result if not x['IsEgress']]
    if ingress_rule_ids:
        cmd = ['ec2', 'revoke-security-group-ingress']
        cmd += ['--group-id', eb_security_group_id['default']]
        cmd += ['--security-group-rule-ids'] + ingress_rule_ids
        aws_cli.run(cmd)

    egress_rule_ids = [x['SecurityGroupRuleId'] for x in result if x['IsEgress']]
    if egress_rule_ids:
        cmd = ['ec2', 'revoke-security-group-egress']
        cmd += ['--group-id', eb_security_group_id['default']]
        cmd += ['--security-group-rule-ids'] + egress_rule_ids
        aws_cli.run(cmd)

    ################################################################################
    print_message('create network acl')

    cmd = ['ec2', 'describe-network-acls']
    cmd += ['--filters', f'Name=vpc-id,Values={eb_vpc_id}']
    cmd += ['--query', 'NetworkAcls[*].{NetworkAclId:NetworkAclId, IsDefault:IsDefault, Entries:Entries}']
    rr = aws_cli.run(cmd)
    rr = rr[0]
    eb_network_acl_id = rr['NetworkAclId']

    cmd = ['ec2', 'create-network-acl-entry']
    cmd += ['--network-acl-id', eb_network_acl_id]
    cmd += ['--rule-number', '10']
    cmd += ['--protocol', 'tcp']
    cmd += ['--port-range', 'From=22,To=22']
    cmd += ['--ingress']
    cmd += ['--rule-action', 'deny']
    cmd += ['--cidr-block', '0.0.0.0/0']
    aws_cli.run(cmd)

    cmd = ['ec2', 'create-network-acl-entry']
    cmd += ['--network-acl-id', eb_network_acl_id]
    cmd += ['--rule-number', '20']
    cmd += ['--protocol', 'tcp']
    cmd += ['--port-range', 'From=3386,To=3386']
    cmd += ['--ingress']
    cmd += ['--rule-action', 'deny']
    cmd += ['--cidr-block', '0.0.0.0/0']
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
    cmd += ['--destination-cidr-block', cidr_subnet['eb']['private_3']]
    cmd += ['--vpc-peering-connection-id', peering_connection_id]
    aws_cli.run(cmd)

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', rds_route_table_id['private']]
    cmd += ['--destination-cidr-block', cidr_subnet['eb']['private_4']]
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

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', rds_route_table_id['private']]
    cmd += ['--destination-cidr-block', cidr_subnet['eb']['public_3']]
    cmd += ['--vpc-peering-connection-id', peering_connection_id]
    aws_cli.run(cmd)

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', rds_route_table_id['private']]
    cmd += ['--destination-cidr-block', cidr_subnet['eb']['public_4']]
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
    cmd += ['--route-table-id', eb_route_table_id['private']]
    cmd += ['--destination-cidr-block', cidr_subnet['rds']['private_3']]
    cmd += ['--vpc-peering-connection-id', peering_connection_id]
    aws_cli.run(cmd)

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', eb_route_table_id['private']]
    cmd += ['--destination-cidr-block', cidr_subnet['rds']['private_4']]
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

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', eb_route_table_id['public']]
    cmd += ['--destination-cidr-block', cidr_subnet['rds']['private_3']]
    cmd += ['--vpc-peering-connection-id', peering_connection_id]
    aws_cli.run(cmd)

    cmd = ['ec2', 'create-route']
    cmd += ['--route-table-id', eb_route_table_id['public']]
    cmd += ['--destination-cidr-block', cidr_subnet['rds']['private_4']]
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
            aws_cli.set_name_tag(network_interface_id, 'nat')
    ################################################################################
    #
    # VPC Endpoint
    #
    ################################################################################
    print_session('vpc endpoint')

    cmd = ['ec2', 'create-vpc-endpoint']
    cmd += ['--vpc-id', eb_vpc_id]
    cmd += ['--vpc-endpoint-type', 'Gateway']
    cmd += ['--service-name', 'com.amazonaws.ap-northeast-2.s3']
    cmd += ['--route-table-ids', eb_route_table_id['private']]
    cmd += ['--policy-document', 'file://aws_iam/aws-ec2-vpc-endpoint-policy-for-s3.json']
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################
print_session('create vpc')

region = options.get('region')
is_target_exists = False

for vpc_env in env.get('vpc', list()):

    if region and vpc_env['AWS_REGION'] != region:
        continue

    is_target_exists = True

    main(vpc_env)

if is_target_exists is False:
    mm = list()
    if region:
        mm.append(region)
    mm = ' in '.join(mm)
    print(f'vpc: {mm} is not found in config.json')
