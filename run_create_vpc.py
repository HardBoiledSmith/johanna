#!/usr/bin/env python
import sys

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

if __name__ == "__main__":
    from run_common import parse_args

    parse_args()

aws_cli = AWSCli()
aws_availability_zone_1 = env['aws']['AWS_AVAILABILITY_ZONE_1']
aws_availability_zone_2 = env['aws']['AWS_AVAILABILITY_ZONE_2']

cidr_vpc = aws_cli.cidr_vpc
cidr_subnet = aws_cli.cidr_subnet

################################################################################
#
# start
#
################################################################################
print_message('get vpc id')

eb_vpc_id = aws_cli.get_vpc_id()
if eb_vpc_id:
    print_message('VPC already exists')
    print 'EB: %s \n' % eb_vpc_id
    print_session('finish python code')
    sys.exit(0)

################################################################################
#
# EB
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
print_message('create iam role')

cmd = ['iam', 'create-role']
cmd += ['--role-name', 'aws-elasticbeanstalk-ec2-role']
cmd += ['--assume-role-policy-document', 'file://aws_iam/aws-elasticbeanstalk-ec2-role.json']
aws_cli.run(cmd)

cmd = ['iam', 'create-role']
cmd += ['--role-name', 'aws-elasticbeanstalk-ec2-worker-role']
cmd += ['--assume-role-policy-document', 'file://aws_iam/aws-elasticbeanstalk-ec2-worker-role.json']
aws_cli.run(cmd)

cmd = ['iam', 'create-role']
cmd += ['--role-name', 'aws-elasticbeanstalk-service-role']
cmd += ['--assume-role-policy-document', 'file://aws_iam/aws-elasticbeanstalk-service-role.json']
aws_cli.run(cmd)

################################################################################
print_message('put iam role policy')

cmd = ['iam', 'put-role-policy']
cmd += ['--role-name', 'aws-elasticbeanstalk-ec2-worker-role']
cmd += ['--policy-name', 'oneClick_aws-elasticbeanstalk-ec2-worker-role']
cmd += ['--policy-document', 'file://aws_iam/oneClick_aws-elasticbeanstalk-ec2-worker-role.json']
aws_cli.run(cmd)

cmd = ['iam', 'put-role-policy']
cmd += ['--role-name', 'aws-elasticbeanstalk-service-role']
cmd += ['--policy-name', 'oneClick_aws-elasticbeanstalk-service-role']
cmd += ['--policy-document', 'file://aws_iam/oneClick_aws-elasticbeanstalk-service-role.json']
aws_cli.run(cmd)

################################################################################
print_message('create application')

cmd = ['elasticbeanstalk', 'create-application']
cmd += ['--application-name', env['elasticbeanstalk']['APPLICATION_NAME']]
aws_cli.run(cmd)

################################################################################
#
# VPC
#
################################################################################
print_session('create vpc')

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

################################################################################
print_message('create nat gateway')  # We use only one NAT gateway at subnet 'public_1'

cmd = ['ec2', 'create-nat-gateway']
cmd += ['--subnet-id', eb_subnet_id['public_1']]
cmd += ['--allocation-id', eb_eip_id]
result = aws_cli.run(cmd)
eb_nat_gateway_id = result['NatGateway']['NatGatewayId']

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
