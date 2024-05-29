#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import re_sub_lines
from run_common import read_file
from run_common import write_file
from run_create_eb_iam import create_iam_profile_for_ec2_instances


def run_create_eb_ramiel_coturn(name, settings, options):
    aws_cli = AWSCli(settings['AWS_REGION'])

    aws_asg_max_value = settings['AWS_ASG_MAX_VALUE']
    aws_asg_min_value = settings['AWS_ASG_MIN_VALUE']
    aws_region = settings['AWS_REGION']
    cname = settings['CNAME']
    eb_application_name = env['elasticbeanstalk']['APPLICATION_NAME']
    git_url = settings['GIT_URL']
    instance_type = settings.get('INSTANCE_TYPE', 't4g.micro')
    phase = env['common']['PHASE']

    ramiel_coturn_dns_a_record_1 = settings.get('RAMIEL_COTURN_DNS_A_RECORD_1')
    ramiel_coturn_dns_a_record_2 = settings.get('RAMIEL_COTURN_DNS_A_RECORD_2')
    if not ramiel_coturn_dns_a_record_1 and not ramiel_coturn_dns_a_record_2:
        print('No DNS A record found')
        raise Exception()

    ramiel_coturn_user_name = settings['RAMIEL_COTURN_USER_NAME']
    ramiel_coturn_user_password = settings['RAMIEL_COTURN_USER_PASSWORD']
    ramiel_coturn_listening_port = settings['RAMIEL_COTURN_LISTENING_PORT']
    ramiel_coturn_listening_port_tls = settings['RAMIEL_COTURN_LISTENING_PORT_TLS']
    ramiel_coturn_min_port = settings['RAMIEL_COTURN_MIN_PORT']
    ramiel_coturn_max_port = settings['RAMIEL_COTURN_MAX_PORT']
    ramiel_coturn_realm = settings['RAMIEL_COTURN_REALM']

    cidr_subnet = aws_cli.cidr_subnet

    str_timestamp = str(int(time.time()))

    zip_filename = f'{name}-{str_timestamp}.zip'

    eb_environment_name = f'{name}-{str_timestamp}'
    eb_environment_name_old = None

    template_path = f'template/{name}'

    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]

    ################################################################################
    print_session(f'create {name}')

    ################################################################################
    print_message('get vpc id')

    rds_vpc_id, eb_vpc_id = aws_cli.get_vpc_id()

    if not eb_vpc_id:
        print('No VPC found')
        raise Exception()

    print_message('get Availability Zones offering required instance type')
    cmd = ['ec2', 'describe-instance-type-offerings']
    cmd += ['--location-type', 'availability-zone']
    cmd += ['--filters', f'Name=instance-type,Values={instance_type}']
    cmd += ['--region', aws_region]
    result = aws_cli.run(cmd)
    azs = [az['Location'] for az in result['InstanceTypeOfferings']]

    ################################################################################
    print_message('get subnet id')

    elb_subnet_id_1 = None
    elb_subnet_id_2 = None
    elb_subnet_id_3 = None
    elb_subnet_id_4 = None
    ec2_subnet_id_1 = None
    ec2_subnet_id_2 = None
    ec2_subnet_id_3 = None
    ec2_subnet_id_4 = None
    cmd = ['ec2', 'describe-subnets']
    result = aws_cli.run(cmd)
    for r in result['Subnets']:
        if r['VpcId'] != eb_vpc_id:
            continue
        if r['AvailabilityZone'] not in azs:
            continue

        if r['CidrBlock'] == cidr_subnet['eb']['public_1']:
            ec2_subnet_id_1 = elb_subnet_id_1 = r['SubnetId']
        if r['CidrBlock'] == cidr_subnet['eb']['public_2']:
            ec2_subnet_id_2 = elb_subnet_id_2 = r['SubnetId']
        if r['CidrBlock'] == cidr_subnet['eb']['public_3']:
            ec2_subnet_id_3 = elb_subnet_id_3 = r['SubnetId']
        if r['CidrBlock'] == cidr_subnet['eb']['public_4']:
            ec2_subnet_id_4 = elb_subnet_id_4 = r['SubnetId']

    ################################################################################
    print_message('get security group id')

    security_group_id = None
    cmd = ['ec2', 'describe-security-groups']
    result = aws_cli.run(cmd)
    for r in result['SecurityGroups']:
        if r['VpcId'] != eb_vpc_id:
            continue

        if r['GroupName'] == 'eb_ramiel_coturn':
            security_group_id = r['GroupId']
            break

    if not security_group_id:
        print('No security group found')
        raise Exception()

    ################################################################################
    print_message('git clone')

    subprocess.Popen(['rm', '-rf', template_path]).communicate()
    subprocess.Popen(['mkdir', '-p', template_path]).communicate()

    branch = options.get('branch', 'master' if phase == 'dv' else phase)
    print(f'branch: {branch}')
    git_command = ['git', 'clone', '--depth=1', '-b', branch, git_url]
    subprocess.Popen(git_command, cwd=template_path).communicate()
    if not os.path.exists(f'{template_path}/ramiel'):
        raise Exception()

    git_hash_app = subprocess.Popen(git_rev, stdout=subprocess.PIPE, cwd=f'{template_path}/ramiel').communicate()[0]

    subprocess.Popen(['rm', '-rf', f'./ramiel/.git'], cwd=f'{template_path}/ramiel').communicate()
    subprocess.Popen(['rm', '-rf', f'./ramiel/.gitignore'], cwd=f'{template_path}/ramiel').communicate()

    ################################################################################
    print_message(f'configuration {name}')

    lines = read_file(
        f'{template_path}/ramiel/ramiel2_dev/coturn/_provisioning/.ebextensions/ramiel_coturn.config.sample')
    lines = re_sub_lines(lines, 'AWS_ASG_MAX_VALUE', aws_asg_max_value)
    lines = re_sub_lines(lines, 'AWS_ASG_MIN_VALUE', aws_asg_min_value)
    lines = re_sub_lines(lines, 'RAMIEL_COTURN_USER_NAME', ramiel_coturn_user_name)
    lines = re_sub_lines(lines, 'RAMIEL_COTURN_USER_PASSWORD', ramiel_coturn_user_password)
    lines = re_sub_lines(lines, 'RAMIEL_COTURN_LISTENING_PORT', ramiel_coturn_listening_port)
    lines = re_sub_lines(lines, 'RAMIEL_COTURN_LISTENING_PORT_TLS', ramiel_coturn_listening_port_tls)
    lines = re_sub_lines(lines, 'RAMIEL_COTURN_MAX_PORT', ramiel_coturn_max_port)
    lines = re_sub_lines(lines, 'RAMIEL_COTURN_MIN_PORT', ramiel_coturn_min_port)
    lines = re_sub_lines(lines, 'RAMIEL_COTURN_REALM', ramiel_coturn_realm)
    write_file(f'{template_path}/ramiel/ramiel2_dev/coturn/_provisioning/.ebextensions/ramiel_coturn.config', lines)

    ################################################################################
    print_message('create iam')

    instance_profile_name, role_arn = create_iam_profile_for_ec2_instances(
        f'{template_path}/ramiel/ramiel2_dev', name, f'{template_path}/ramiel/ramiel2_dev/coturn/_provisioning/iam')
    print_message('wait 10 seconds to let iam role and policy propagated to all regions...')
    time.sleep(10)

    ################################################################################
    print_message('check previous version')

    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--application-name', eb_application_name]
    result = aws_cli.run(cmd)

    for r in result['Environments']:
        if 'CNAME' not in r:
            continue

        if r['CNAME'] == f'{cname}.{aws_region}.elasticbeanstalk.com':
            if r['Status'] == 'Terminated':
                continue
            elif r['Status'] != 'Ready':
                print('previous version is not ready.')
                raise Exception()

            eb_environment_name_old = r['EnvironmentName']
            cname += '-%s' % str_timestamp
            break

    ################################################################################
    print_message('create storage location')

    cmd = ['elasticbeanstalk', 'create-storage-location']
    result = aws_cli.run(cmd)

    s3_bucket = result['S3Bucket']
    s3_zip_filename = '/'.join(['s3://' + s3_bucket, eb_application_name, zip_filename])

    ################################################################################
    print_message('create application version')

    file_list = list()
    file_list.append('.ebextensions')
    file_list.append('.platform')
    file_list.append('Procfile')
    file_list.append('application.py')

    for ff in file_list:
        cmd = ['mv', f'ramiel/ramiel2_dev/coturn/_provisioning/{ff}', '.']
        subprocess.Popen(cmd, cwd=template_path).communicate()

    cmd = ['rm', '-rf', 'ramiel']
    subprocess.Popen(cmd, cwd=template_path).communicate()

    cmd = ['zip', '-r', zip_filename, '.', '.ebextensions']
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=template_path).communicate()

    cmd = ['s3', 'cp', zip_filename, s3_zip_filename]
    aws_cli.run(cmd, cwd=template_path)

    cmd = ['rm', '-rf', zip_filename]
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=template_path).communicate()

    cmd = ['elasticbeanstalk', 'create-application-version']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--source-bundle', 'S3Bucket="%s",S3Key="%s/%s"' % (s3_bucket, eb_application_name, zip_filename)]
    cmd += ['--version-label', eb_environment_name]
    aws_cli.run(cmd, cwd=template_path)

    ################################################################################
    print_message('update s3 policy of storage location')

    cmd = ['s3api', 'get-bucket-policy']
    cmd += ['--bucket', s3_bucket]
    rr = aws_cli.run(cmd)
    rr = rr['Policy']

    account_id = aws_cli.get_caller_account_id()
    ppp = fr'arn:aws:iam::{account_id}:role/aws-elasticbeanstalk-(?:[a-z]+-ec2|ec2)-role'
    role_list = re.findall(ppp, rr)

    role_list = set(role_list)
    role_list.add(role_arn)
    role_list = list(role_list)

    lines = read_file('aws_iam/aws-elasticbeanstalk-storage-policy.json')
    lines = re_sub_lines(lines, 'BUCKET_NAME', s3_bucket)
    lines = re_sub_lines(lines, 'AWS_ACCOUNT_ID', account_id)
    elb_account_id = aws_cli.get_elb_account_id(aws_region)
    lines = re_sub_lines(lines, 'ELB_ACCOUNT_ID', elb_account_id)
    lines = re_sub_lines(lines, 'EC2_ROLE_LIST', json.dumps(role_list))
    pp = ' '.join(lines)
    pp = json.loads(pp)

    cmd = ['s3api', 'put-bucket-policy']
    cmd += ['--bucket', s3_bucket]
    cmd += ['--policy', json.dumps(pp)]
    aws_cli.run(cmd)

    ################################################################################
    print_message('create environment %s' % name)

    option_settings = list()

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'InstanceType'
    oo['Value'] = instance_type
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'IamInstanceProfile'
    oo['Value'] = instance_profile_name
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'SecurityGroups'
    oo['Value'] = security_group_id
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:autoscaling:launchconfiguration'
    oo['OptionName'] = 'RootVolumeType'
    oo['Value'] = 'gp3'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'AssociatePublicIpAddress'
    oo['Value'] = 'true'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'ELBScheme'
    oo['Value'] = 'public'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'ELBSubnets'
    oo['Value'] = ','.join([ss for ss in [elb_subnet_id_1, elb_subnet_id_2, elb_subnet_id_3, elb_subnet_id_4] if ss])
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'Subnets'
    oo['Value'] = ','.join([ss for ss in [ec2_subnet_id_1, ec2_subnet_id_2, ec2_subnet_id_3, ec2_subnet_id_4] if ss])
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:ec2:vpc'
    oo['OptionName'] = 'VPCId'
    oo['Value'] = eb_vpc_id
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:environment'
    oo['OptionName'] = 'EnvironmentType'
    oo['Value'] = 'LoadBalanced'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:environment'
    oo['OptionName'] = 'LoadBalancerType'
    oo['Value'] = 'application'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:environment'
    oo['OptionName'] = 'ServiceRole'
    oo['Value'] = 'aws-elasticbeanstalk-service-role'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:healthreporting:system'
    oo['OptionName'] = 'ConfigDocument'
    cw_instance = dict()
    cw_instance['RootFilesystemUtil'] = 60
    cw_instance['InstanceHealth'] = 60
    cw_instance['CPUIdle'] = 60
    cw = dict()
    cw['Instance'] = cw_instance
    cfg_doc = dict()
    cfg_doc['CloudWatchMetrics'] = cw
    cfg_doc['Version'] = 1
    oo['Value'] = json.dumps(cfg_doc)
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:healthreporting:system'
    oo['OptionName'] = 'EnhancedHealthAuthEnabled'
    oo['Value'] = 'true'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:cloudwatch:logs'
    oo['OptionName'] = 'StreamLogs'
    oo['Value'] = 'true'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:cloudwatch:logs'
    oo['OptionName'] = 'DeleteOnTerminate'
    oo['Value'] = 'true'
    option_settings.append(oo)

    oo = dict()
    oo['Namespace'] = 'aws:elasticbeanstalk:cloudwatch:logs'
    oo['OptionName'] = 'RetentionInDays'
    oo['Value'] = '3'
    option_settings.append(oo)

    option_settings = json.dumps(option_settings)

    tag0 = 'Key=git_hash_johanna,Value=%s' % git_hash_johanna.decode('utf-8').strip()
    tag1 = 'Key=git_hash_%s,Value=%s' % (name, git_hash_app.decode('utf-8').strip())

    cmd = ['elasticbeanstalk', 'create-environment']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--cname-prefix', cname]
    cmd += ['--environment-name', eb_environment_name]
    cmd += ['--option-settings', option_settings]
    cmd += ['--solution-stack-name', '64bit Amazon Linux 2 v3.6.0 running Python 3.8']
    cmd += ['--tags', tag0, tag1]
    cmd += ['--version-label', eb_environment_name]
    aws_cli.run(cmd, cwd=template_path)

    elapsed_time = 0
    while True:
        cmd = ['elasticbeanstalk', 'describe-environments']
        cmd += ['--application-name', eb_application_name]
        cmd += ['--environment-name', eb_environment_name]
        result = aws_cli.run(cmd)

        ee = result['Environments'][0]
        print(json.dumps(ee, sort_keys=True, indent=4))
        if ee.get('Health', '') == 'Green' and ee.get('Status', '') == 'Ready':
            break

        print(f'creating... (elapsed time: \'{elapsed_time}\' seconds)')
        time.sleep(5)
        elapsed_time += 5

        if elapsed_time > 60 * 30:
            raise Exception()

    subprocess.Popen(['rm', '-rf', f'./{name}'], cwd=template_path).communicate()

    eb_environment_name = 'ramiel-coturn-1716978682'

    ################################################################################
    print_message('swap FIP if the previous version exists')

    cmd = ['route53', 'list-hosted-zones']
    cmd += ['--query', 'HostedZones[?Name==\'hbsmith.io.\'].Id']
    rr = aws_cli.run(cmd)
    hosted_zone_id = rr[0]

    if not hosted_zone_id:
        print('No hosted zone found')
        if phase == 'op':
            raise Exception()
        else:
            print('only for op phase')
            return

    cmd = ['route53', 'list-resource-record-sets']
    cmd += ['--hosted-zone-id', hosted_zone_id]
    cmd += ['--query',
            'ResourceRecordSets[?Type==\'A\' '
            f'&& (Name==\'{ramiel_coturn_dns_a_record_1}.\' || \'{ramiel_coturn_dns_a_record_2}.\')].Name']
    rr = aws_cli.run(cmd)
    a_records = rr

    if len(a_records) != 2:
        print('No DNS A record found')
        raise Exception()
    if f'{ramiel_coturn_dns_a_record_1}.' not in a_records or f'{ramiel_coturn_dns_a_record_2}.' not in a_records:
        print(f'Either {ramiel_coturn_dns_a_record_1} or {ramiel_coturn_dns_a_record_2} found in {a_records}')
        raise Exception()

    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--application-name', eb_application_name]
    cmd += ['--environment-name', eb_environment_name]
    cmd += ['--query', 'Environments[0].EnvironmentId']
    env_id = aws_cli.run(cmd)

    if not env_id:
        print('No environment id found')
        raise Exception()

    cmd = ['elasticbeanstalk', 'describe-instances-health']
    cmd += ['--environment-id', env_id]
    cmd += ['--attribute-names', 'All']
    cmd += ['--query', 'InstanceHealthList[].InstanceId']
    instance_ids = aws_cli.run(cmd)

    if not instance_ids:
        print('No instance id found')
        raise Exception()
    if len(instance_ids) != 2:
        print(f'Wrong instance count: {len(instance_ids)} != 2')
        raise Exception()

    cmd = ['ec2', 'describe-instances']
    cmd += ['--instance-ids', instance_ids[0], instance_ids[1]]
    cmd += ['--query', 'Reservations[*].Instances[*].PublicIpAddress']
    public_ips = aws_cli.run(cmd)

    try:
        public_ips = [ii[0] for ii in public_ips if ii]
    except Exception:
        print('No public ip found')
        raise Exception()
    if len(public_ips) != 2:
        print(f'Wrong public ip count: {len(public_ips)} != 2')
        raise Exception()

    dd = dict()
    dd['Changes'] = [
        {
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": ramiel_coturn_dns_a_record_1,
                "Type": "A",
                "TTL": 60,
                "ResourceRecords": [
                    {
                        "Value": public_ips[0]
                    }
                ]
            }
        },
        {
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": ramiel_coturn_dns_a_record_2,
                "Type": "A",
                "TTL": 60,
                "ResourceRecords": [
                    {
                        "Value": public_ips[1]
                    }
                ]
            }
        },
    ]

    cmd = ['route53', 'change-resource-record-sets']
    cmd += ['--hosted-zone-id', hosted_zone_id]
    cmd += ['--change-batch', json.dumps(dd)]
    aws_cli.run(cmd)

    ################################################################################
    print_message('swap CNAME if the previous version exists')

    if eb_environment_name_old:
        cmd = ['elasticbeanstalk', 'swap-environment-cnames']
        cmd += ['--source-environment-name', eb_environment_name_old]
        cmd += ['--destination-environment-name', eb_environment_name]
        aws_cli.run(cmd)
