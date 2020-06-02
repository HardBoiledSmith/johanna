#!/usr/bin/env python3
import json
import time

from env import env
from run_common import AWSCli
from run_common import print_message


def get_rds_endpoint(aws, db_cluster_id):
    cmd = ['rds', 'describe-db-cluster-endpoints']
    cmd += ['--db-cluster-identifier', db_cluster_id]
    rr = aws.run(cmd)
    for dd in rr['DBClusterEndpoints']:
        if dd['EndpointType'] == 'WRITER':
            return dd['Endpoint']


def have_parameter_store(settings):
    for pp in settings['ENV_VARIABLES']:
        if 'PARAMETER_STORE' == pp['type']:
            return True

    return False


def create_iam_for_codebuild_vpc(name, settings, subnet_id_1):
    region = settings['AWS_VPC_REGION']
    account_id = settings['CANONICAL_ID']
    aws_cli = AWSCli(region)

    nn = name.replace('_', '-')
    role_name = f'aws-codebuild-{nn}-role'
    if not aws_cli.get_iam_role(role_name):
        print_message(f'create iam role: {role_name}')

        dd = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {
                        'Service': 'codebuild.amazonaws.com'
                    },
                    'Action': 'sts:AssumeRole'
                }
            ]
        }
        cmd = ['iam', 'create-role']
        cmd += ['--role-name', role_name]
        cmd += ['--assume-role-policy-document', json.dumps(dd)]
        aws_cli.run(cmd)

    policy_name = f'aws-codebuild-{nn}-policy'
    if not aws_cli.get_iam_role_policy(role_name, policy_name):
        print_message(f'create iam role policy: {policy_name}')
        dd = {
            'Version': '2012-10-17',
            'Statement': []
        }

        pp = {
            'Effect': 'Allow',
            'Action': [
                'logs:CreateLogGroup',
                'logs:CreateLogStream',
                'logs:PutLogEvents'
            ],
            'Resource': '*'
        }
        dd['Statement'].append(pp)

        pp = {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateNetworkInterface",
                "ec2:DescribeDhcpOptions",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DeleteNetworkInterface",
                "ec2:DescribeSubnets",
                "ec2:DescribeSecurityGroups",
                "ec2:DescribeVpcs"
            ],
            "Resource": "*"
        }
        dd['Statement'].append(pp)

        pp = {
            'Effect': 'Allow',
            'Action': [
                'ec2:CreateNetworkInterfacePermission'
            ],
            'Resource': f'arn:aws:ec2:{region}:*:network-interface/*',
            'Condition': {
                'StringEquals': {
                    'ec2:Subnet': [
                        f'arn:aws:ec2:{region}:{account_id}:subnet/{subnet_id_1}'
                    ],
                    'ec2:AuthorizedService': 'codebuild.amazonaws.com'
                }
            }
        }
        dd['Statement'].append(pp)

        if have_parameter_store(settings):
            pp = {
                'Effect': 'Allow',
                'Action': 'ssm:GetParameters',
                'Resource': f'arn:aws:ssm:{region}:*:parameter/CodeBuild/*'
            }
            dd['Statement'].append(pp)

        cmd = ['iam', 'put-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-name', policy_name]
        cmd += ['--policy-document', json.dumps(dd)]
        aws_cli.run(cmd)
        time.sleep(120)

    return role_name


def get_eb_public_subnet_and_security_group_id():
    aws_cli = AWSCli()
    cidr_subnet = aws_cli.cidr_subnet

    print_message('get vpc id')

    _, eb_vpc_id = aws_cli.get_vpc_id()

    if not eb_vpc_id:
        print('ERROR!!! No VPC found')
        raise Exception()

    print_message('get subnet id')

    subnet_id_1 = None
    cmd = ['ec2', 'describe-subnets']
    rr = aws_cli.run(cmd)
    for r in rr['Subnets']:
        if r['VpcId'] != eb_vpc_id:
            continue
        if r['CidrBlock'] == cidr_subnet['eb']['private_1']:
            subnet_id_1 = r['SubnetId']

    print_message('get security group id')

    security_group_id = None
    cmd = ['ec2', 'describe-security-groups']
    rr = aws_cli.run(cmd)
    for r in rr['SecurityGroups']:
        if r['VpcId'] != eb_vpc_id:
            continue
        if r['GroupName'] == 'eb_private':
            security_group_id = r['GroupId']
            break

    return [subnet_id_1], security_group_id


def run_create_codebuild_vpc(name, settings):
    aws_cli = AWSCli()

    git_branch = settings['BRANCH']
    build_spec = settings['BUILD_SPEC']
    build_timeout = settings['BUILD_TIMEOUT']
    compute_type = settings['ENV_COMPUTE_TYPE']
    description = settings['DESCRIPTION']
    git_repo = settings['GITHUB_REPO']
    github_token = settings['GITHUB_TOKEN']
    image = settings['IMAGE']

    ################################################################################
    print_message('check previous version')

    cmd = ['codebuild', 'list-projects']
    result = aws_cli.run(cmd)
    need_update = name in result['projects']

    ################################################################################
    print_message('import source credentials')

    cmd = ['codebuild', 'import-source-credentials']
    cmd += ['--token', github_token]
    cmd += ['--server-type', 'GITHUB']
    cmd += ['--auth-type', 'PERSONAL_ACCESS_TOKEN']
    aws_cli.run(cmd)

    ################################################################################
    print_message('set environment variable')

    env_list = []
    end_point = get_rds_endpoint(aws_cli, env['rds']['DB_CLUSTER_ID'])

    for pp in settings['ENV_VARIABLES']:
        if 'PARAMETER_STORE' == pp['type']:
            nn = '/CodeBuild/%s/%s' % (name, pp['name'])
            cmd = ['ssm', 'get-parameter', '--name', nn]
            aws_cli.run(cmd)

            pp['value'] = nn

        env_list.append(pp)
    env_list.append({
        "name": "HOST",
        "value": end_point,
        "type": "PLAINTEXT"
    })

    _, eb_vpc_id = aws_cli.get_vpc_id()
    subnet_ids, security_group_id = get_eb_public_subnet_and_security_group_id()

    role_name = create_iam_for_codebuild_vpc(name, settings, subnet_ids[0])
    role_arn = aws_cli.get_role_arn(role_name)

    ################################################################################

    config = {
        "name": name,
        "description": description,
        "source": {
            "type": "GITHUB",
            "location": git_repo,
            "gitCloneDepth": 0,
            "buildspec": build_spec,
            "auth": {
                "type": "OAUTH",
                "resource": github_token
            },
            "insecureSsl": True,
            "sourceIdentifier": git_branch
        },
        "artifacts": {
            "type": "NO_ARTIFACTS"
        },
        "cache": {
            "type": "NO_CACHE"
        },
        "environment": {
            "type": "LINUX_CONTAINER",
            "image": image,
            "computeType": compute_type,
            "environmentVariables": env_list
        },
        "serviceRole": role_arn,
        "timeoutInMinutes": build_timeout,
        "badgeEnabled": True,
        "vpcConfig": {
            "vpcId": eb_vpc_id,
            "subnets": subnet_ids,
            "securityGroupIds": [security_group_id]
        }
    }
    config = json.dumps(config)

    if need_update:
        print_message('update project: %s' % name)

        cmd = ['codebuild', 'update-project', '--cli-input-json', config]
        aws_cli.run(cmd)
        return

    print_message('create project: %s' % name)

    cmd = ['codebuild', 'create-project', '--cli-input-json', config]
    aws_cli.run(cmd)
