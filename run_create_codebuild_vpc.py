#!/usr/bin/env python3.11
import json
import time

from run_common import AWSCli
from run_common import print_message
from run_create_codebuild_common import create_base_iam_policy
from run_create_codebuild_common import create_iam_service_role
from run_create_codebuild_common import create_managed_secret_iam_policy
from run_create_codebuild_common import have_parameter_store


def create_vpc_iam_policy(aws_cli, name, settings, role_name, subnet_id):
    aws_region = settings['AWS_REGION']

    account_id = aws_cli.get_caller_account_id()

    policy_name = f'CodeBuildVpcPolicy-{name}-{aws_region}'
    policy_arn = f'arn:aws:iam::{account_id}:policy/service-role/{policy_name}'
    if not aws_cli.get_iam_policy(policy_arn):
        print_message(f'create iam policy: {policy_name}')

        dd = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': [
                        'ec2:CreateNetworkInterface',
                        'ec2:DescribeDhcpOptions',
                        'ec2:DescribeNetworkInterfaces',
                        'ec2:DeleteNetworkInterface',
                        'ec2:DescribeSubnets',
                        'ec2:DescribeSecurityGroups',
                        'ec2:DescribeVpcs'
                    ],
                    'Resource': '*'
                },
                {
                    'Effect': 'Allow',
                    'Action': [
                        'ec2:CreateNetworkInterfacePermission'
                    ],
                    'Resource': f'arn:aws:ec2:{aws_region}:{account_id}:network-interface/*',
                    'Condition': {
                        'StringEquals': {
                            'ec2:Subnet': [
                                f'arn:aws:ec2:{aws_region}:{account_id}:subnet/{subnet_id}'
                            ],
                            'ec2:AuthorizedService': 'codebuild.amazonaws.com'
                        }
                    }
                }
            ]
        }

        cmd = ['iam', 'create-policy']
        cmd += ['--policy-name', policy_name]
        cmd += ['--path', '/service-role/']
        cmd += ['--description', 'Policy used in trust relationship with CodeBuild']
        cmd += ['--policy-document', json.dumps(dd)]
        result = aws_cli.run(cmd)

        policy_arn = result['Policy']['Arn']

        cmd = ['iam', 'attach-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-arn', policy_arn]
        aws_cli.run(cmd)


def get_eb_private_subnet_and_security_group_id(aws_cli):
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

    return subnet_id_1, security_group_id


def run_create_vpc_project(name, settings):
    aws_cli = AWSCli(settings['AWS_REGION'])

    git_branch = settings['BRANCH']
    build_spec = settings['BUILD_SPEC']
    build_timeout = settings['BUILD_TIMEOUT']
    compute_type = settings['ENV_COMPUTE_TYPE']
    description = settings['DESCRIPTION']
    git_repo = settings['GITHUB_REPO']
    image = settings['IMAGE']
    container_type = settings.get('CONTAINER_TYPE', 'LINUX_CONTAINER')

    ################################################################################
    print_message('check previous version')

    cmd = ['codebuild', 'list-projects']
    result = aws_cli.run(cmd)
    need_update = name in result['projects']

    ################################################################################
    print_message('create iam service role')

    service_role_name = create_iam_service_role(aws_cli, name)
    create_base_iam_policy(aws_cli, name, settings, service_role_name)

    if have_parameter_store(settings):
        create_managed_secret_iam_policy(aws_cli, name, settings, service_role_name)

    subnet_id, security_group_id = get_eb_private_subnet_and_security_group_id(aws_cli)
    create_vpc_iam_policy(aws_cli, name, settings, service_role_name, subnet_id)

    print_message('wait 30 seconds to let iam role and policy propagated to all regions...')
    time.sleep(30)

    service_role_arn = aws_cli.get_role_arn(service_role_name)

    ################################################################################
    print_message('set environment variable')

    env_list = []
    for pp in settings['ENV_VARIABLES']:
        if 'PARAMETER_STORE' == pp['type']:
            nn = f"/CodeBuild/{name}/{pp['name']}"
            cmd = ['ssm', 'get-parameter', '--name', nn]
            aws_cli.run(cmd)

            pp['value'] = nn

        env_list.append(pp)

    ################################################################################
    _, eb_vpc_id = aws_cli.get_vpc_id()

    config = {
        "name": name,
        "description": description,
        "source": {
            "type": "GITHUB",
            "location": git_repo,
            "gitCloneDepth": 0,
            "buildspec": build_spec,
            "auth": {
                "type": "OAUTH"
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
            "type": container_type,
            "image": image,
            "computeType": compute_type,
            "environmentVariables": env_list
        },
        "serviceRole": service_role_arn,
        "timeoutInMinutes": build_timeout,
        "badgeEnabled": True,
        "vpcConfig": {
            "vpcId": eb_vpc_id,
            "subnets": [subnet_id],
            "securityGroupIds": [security_group_id]
        }
    }
    config = json.dumps(config)

    if need_update:
        print_message(f'update project: {name}')
        cmd = ['codebuild', 'update-project', '--cli-input-json', config, '--source-version', git_branch]
        aws_cli.run(cmd)
    else:
        print_message(f'create project: {name}')
        cmd = ['codebuild', 'create-project', '--cli-input-json', config, '--source-version', git_branch]
        aws_cli.run(cmd)
