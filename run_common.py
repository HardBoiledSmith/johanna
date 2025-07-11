#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import time
from optparse import OptionParser

from env import env

try:
    # noinspection PyShadowingBuiltins, PyUnresolvedReferences
    input = raw_input
except NameError:
    pass


def _confirm_phase():
    phase = env['common']['PHASE']
    service_name = env['common'].get('SERVICE_NAME', '(none)')
    print('Your current environment values are below')
    print('-' * 80)
    print('\tSERVICE_NAME        : %s' % service_name)
    print('\tPHASE               : %s' % phase)
    if 'template' in env:
        print('\tTEMPLATE            : %s' % env['template']['NAME'])
    if 'elasticbeanstalk' in env:
        eb = env['elasticbeanstalk']
        for eb_env in eb['ENVIRONMENTS']:
            aws_default_region = env['aws']['AWS_DEFAULT_REGION'] \
                if 'AWS_DEFAULT_REGION' not in eb_env \
                else eb_env['AWS_DEFAULT_REGION']
            print('\tCNAME of %-10s : %-20s (%s)' % (eb_env['NAME'], eb_env['CNAME'], aws_default_region))
    print('-' * 80)

    answer = input('Please type in the name of phase \'%s\' to confirm: ' % phase)
    if answer != phase:
        print('The execution is canceled.')
        sys.exit(0)


class AWSCli:
    cidr_vpc = dict()
    cidr_vpc['rds'] = env['common']['AWS_VPC_RDS']
    cidr_vpc['eb'] = env['common']['AWS_VPC_EB']

    cidr_subnet = dict()
    cidr_subnet['rds'] = dict()
    cidr_subnet['rds']['private_1'] = env['common']['AWS_SUBNET_RDS_PRIVATE_1']
    cidr_subnet['rds']['private_2'] = env['common']['AWS_SUBNET_RDS_PRIVATE_2']
    cidr_subnet['rds']['private_3'] = env['common']['AWS_SUBNET_RDS_PRIVATE_3']
    cidr_subnet['rds']['private_4'] = env['common']['AWS_SUBNET_RDS_PRIVATE_4']
    cidr_subnet['eb'] = dict()
    cidr_subnet['eb']['private_1'] = env['common']['AWS_SUBNET_EB_PRIVATE_1']
    cidr_subnet['eb']['private_2'] = env['common']['AWS_SUBNET_EB_PRIVATE_2']
    cidr_subnet['eb']['private_3'] = env['common']['AWS_SUBNET_EB_PRIVATE_3']
    cidr_subnet['eb']['private_4'] = env['common']['AWS_SUBNET_EB_PRIVATE_4']
    cidr_subnet['eb']['public_1'] = env['common']['AWS_SUBNET_EB_PUBLIC_1']
    cidr_subnet['eb']['public_2'] = env['common']['AWS_SUBNET_EB_PUBLIC_2']
    cidr_subnet['eb']['public_3'] = env['common']['AWS_SUBNET_EB_PUBLIC_3']
    cidr_subnet['eb']['public_4'] = env['common']['AWS_SUBNET_EB_PUBLIC_4']

    def __init__(self, aws_default_region=None, aws_access_key=None, aws_secret_access_key=None,
                 aws_session_token=None):
        if not env['aws'].get('AWS_ACCESS_KEY_ID') or \
                not env['aws'].get('AWS_SECRET_ACCESS_KEY') or \
                not env['aws'].get('AWS_DEFAULT_REGION'):
            raise Exception()

        self.env = dict(os.environ)
        self.env['AWS_ACCESS_KEY_ID'] = env['aws']['AWS_ACCESS_KEY_ID'] \
            if not aws_access_key \
            else aws_access_key
        self.env['AWS_SECRET_ACCESS_KEY'] = env['aws']['AWS_SECRET_ACCESS_KEY'] \
            if not aws_secret_access_key \
            else aws_secret_access_key
        self.env['AWS_REGION'] = self.env['AWS_DEFAULT_REGION'] = env['aws']['AWS_DEFAULT_REGION'] \
            if not aws_default_region \
            else aws_default_region
        self.env['AWS_DEFAULT_OUTPUT'] = 'json'
        if aws_session_token:
            self.env['AWS_SESSION_TOKEN'] = aws_session_token

    def run(self, args, cwd=None, ignore_error=None):
        args = ['aws'] + args
        if ignore_error:
            print('\n>> command(ignore error): [%s]' % self.env['AWS_DEFAULT_REGION'], end=" ")
        else:
            print('\n>> command: [%s]' % self.env['AWS_DEFAULT_REGION'], end=" ")
        print(' '.join(args))
        _p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              cwd=cwd, env=self.env)
        result, error = _p.communicate()
        # noinspection PyUnresolvedReferences
        result = result.decode('utf-8')

        if error:
            print(error.decode('utf-8'))
            if not ignore_error:
                raise Exception()

        if _p.returncode != 0:
            print('command returns: %s' % _p.returncode)
            if not ignore_error:
                raise Exception()

        if args[0] == 'aws':
            # noinspection PyBroadException
            try:
                return json.loads(result)
            except Exception:
                return result
        elif args[0] == 'eb':
            return result

        return dict()

    def get_vpc_id(self):
        rds_vpc_id = None
        cmd = ['ec2', 'describe-vpcs']
        cmd += [f"--filters=Name=cidr,Values={self.cidr_vpc['rds']}"]
        result = self.run(cmd)
        if len(result['Vpcs']) == 1:
            rds_vpc_id = dict(result['Vpcs'][0])['VpcId']

        eb_vpc_id = None
        cmd = ['ec2', 'describe-vpcs']
        cmd += [f"--filters=Name=cidr,Values={self.cidr_vpc['eb']}"]
        result = self.run(cmd)
        if len(result['Vpcs']) == 1:
            eb_vpc_id = dict(result['Vpcs'][0])['VpcId']

        return rds_vpc_id, eb_vpc_id

    def get_elasticache_address(self):
        engine = env['elasticache']['ENGINE']
        if engine != 'redis':
            raise Exception()
        cache_cluster_id = env['elasticache'].get('CACHE_CLUSTER_ID')
        if cache_cluster_id:
            cmd = ['elasticache', 'describe-cache-clusters']
            cmd += ['--show-cache-node-info']
            cmd += ['--show-cache-clusters-not-in-replication-groups']

            elapsed_time = 0
            cache_address = None
            while not cache_address:
                result = self.run(cmd)

                # noinspection PyBroadException
                try:
                    for cache_cluster in result['CacheClusters']:
                        cache_cluster = dict(cache_cluster)

                        if cache_cluster['CacheClusterStatus'] != 'available':
                            continue

                        if cache_cluster['CacheClusterId'] != cache_cluster_id:
                            continue

                        cache_nodes = list(cache_cluster['CacheNodes'])

                        if len(cache_nodes) < 1:
                            continue

                        cache_endpoint = cache_nodes[0]['Endpoint']
                        cache_address = cache_endpoint['Address']

                        if cache_address:
                            return cache_address
                except Exception:
                    pass

                print('waiting for a new elasticache... (elapsed time: \'%d\' seconds)' % elapsed_time)
                time.sleep(5)
                elapsed_time += 5

                if elapsed_time > 60 * 30:
                    raise Exception()

        replication_group_id = env['elasticache'].get('REPLICATION_GROUP_ID')
        if replication_group_id:
            cmd = ['elasticache', 'describe-replication-groups']

            elapsed_time = 0
            cfg_address = None
            while not cfg_address:
                result = self.run(cmd)

                # noinspection PyBroadException
                try:
                    for replication_group in result['ReplicationGroups']:
                        replication_group = dict(replication_group)

                        if replication_group['Status'] != 'available':
                            continue

                        if replication_group['ReplicationGroupId'] != replication_group_id:
                            continue

                        cfg_endpoint = replication_group['ConfigurationEndpoint']
                        cfg_address = cfg_endpoint['Address']

                        if cfg_address:
                            return cfg_address
                except Exception:
                    pass

                print('waiting for a new elasticache... (elapsed time: \'%d\' seconds)' % elapsed_time)
                time.sleep(5)
                elapsed_time += 5

                if elapsed_time > 60 * 30:
                    raise Exception()

    def get_elb_account_id(self, region):
        acc_map = {
            'us-east-1': "127311923021",
            'us-west-2': "797873946194",
            'us-west-1': "027434742980",
            'eu-west-1': "156460612806",
            'eu-central-1': "054676820928",
            'ap-southeast-1': "114774131450",
            'ap-northeast-1': "582318560864",
            'ap-southeast-2': "783225319266",
            'ap-northeast-2': "600734575887",
            'sa-east-1': "507241528517",
            'cn-north-1': "638102146993"
        }
        return acc_map[region]

    def get_caller_account_id(self):
        cmd = ['sts', 'get-caller-identity']
        result = self.run(cmd)
        return result['Account']

    def get_rds_address(self, read_replica=None):
        cluster_id = env['rds']['DB_CLUSTER_ID']
        cmd = ['rds', 'describe-db-clusters']

        elapsed_time = 0
        db_address = None
        while not db_address:
            result = self.run(cmd)

            # noinspection PyBroadException
            try:
                for db_cluster in result['DBClusters']:
                    db_cluster = dict(db_cluster)

                    if db_cluster['Status'] != 'available':
                        continue

                    if db_cluster['DBClusterIdentifier'] != cluster_id:
                        continue

                    if read_replica and 'ReaderEndpoint' not in db_cluster:
                        continue

                    db_address = db_cluster['Endpoint']

                    if read_replica:
                        db_address = db_cluster['ReaderEndpoint']

                    if db_address:
                        return db_address
            except Exception:
                pass

            print('waiting for a new database... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

            if elapsed_time > 60 * 30:
                raise Exception()

    def get_role_arn(self, role_name):
        cmd = ['iam', 'get-role']
        cmd += ['--role-name', role_name]
        result = self.run(cmd)

        # noinspection PyTypeChecker
        return result['Role']['Arn']

    def get_topic_arn(self, topic_name):
        cmd = ['sns', 'list-topics']
        result = self.run(cmd)

        for topic in result['Topics']:
            suffix = ':%s' % topic_name
            # noinspection PyTypeChecker
            arn = topic['TopicArn']
            if arn.endswith(suffix):
                return arn

        return

    def get_temp_bucket(self):
        default_region = env['aws']['AWS_DEFAULT_REGION']

        cmd = ['s3api', 'list-buckets']

        result = self.run(cmd)
        for bucket in result['Buckets']:
            bucket = dict(bucket)

            pattern = 'johanna-%s-[0-9]+' % default_region
            name = bucket['Name']
            if re.match(pattern, name):
                return name

        timestamp = int(time.time())
        bucket_name = 'johanna-%s-%s' % (default_region, timestamp)

        cmd = ['s3api', 'create-bucket', '--bucket', bucket_name, '--region', default_region,
               '--create-bucket-configuration', 'LocationConstraint=%s' % default_region]
        self.run(cmd)

        cmd = ['s3api', 'head-bucket', '--bucket', bucket_name]

        elapsed_time = 0
        while True:
            result = self.run(cmd)

            if len(result) == 0:
                break

            print('creating bucket... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

        return bucket_name

    def get_iam_role(self, role_name):
        cmd = ['iam', 'get-role']
        cmd += ['--role-name', role_name]
        return self.run(cmd, ignore_error=True)

    def get_iam_role_policy(self, role_name, policy_name):
        cmd = ['iam', 'get-role-policy']
        cmd += ['--role-name', role_name]
        cmd += ['--policy-name', policy_name]
        return self.run(cmd, ignore_error=True)

    def get_iam_user(self, user_name=None):
        cmd = ['iam', 'get-user']
        if user_name:
            cmd += ['--user-name', user_name]
        return self.run(cmd, ignore_error=True)

    def get_iam_user_policy(self, user_name, policy_name):
        cmd = ['iam', 'get-user-policy']
        cmd += ['--user-name', user_name]
        cmd += ['--policy-name', policy_name]
        return self.run(cmd, ignore_error=True)

    def get_iam_policy(self, policy_arn):
        cmd = ['iam', 'get-policy']
        cmd += ['--policy-arn', policy_arn]
        return self.run(cmd, ignore_error=True)

    def get_acm_certificate_id(self, domain):
        cmd = ['acm', 'list-certificates']
        cmd += ['--certificate-statuses', 'ISSUED']
        result = self.run(cmd)

        for cl in result['CertificateSummaryList']:
            if cl['DomainName'] == domain:
                return cl['CertificateArn']

        raise Exception()

    def set_name_tag(self, resource_id, name):
        cmd = ['ec2', 'create-tags']
        cmd += ['--resources', resource_id]
        cmd += ['--tags', f'Key=Name,Value={name}']
        self.run(cmd)

    def wait_terminate_lambda(self):
        cmd = ['lambda', 'list-functions']

        elapsed_time = 0
        while True:
            result = self.run(cmd)
            if len(result['Functions']) == 0:
                break

            print('terminating the lambda... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

    def wait_terminate_rds(self):
        cmd = ['rds', 'describe-db-instances']

        elapsed_time = 0
        while True:
            result = self.run(cmd)
            if len(result['DBInstances']) == 0:
                break

            print('terminating the rds... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

        cmd = ['rds', 'describe-db-clusters']

        while True:
            result = self.run(cmd)
            if len(result['DBClusters']) == 0:
                break

            print('terminating the rds... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

    def wait_terminate_elasticache(self):
        cmd = ['elasticache', 'describe-cache-clusters']

        elapsed_time = 0
        while True:
            result = self.run(cmd)
            if len(result['CacheClusters']) == 0:
                break

            print('terminating the elasticache... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

    def wait_terminate_eb(self):
        cmd = ['ec2', 'describe-instances']

        elapsed_time = 0
        while True:
            result = self.run(cmd)
            count = 0
            for r in result['Reservations']:
                for instance in r.get('Instances'):
                    if instance['State']['Name'] != 'terminated':
                        count += 1

            if count == 0:
                break

            print('terminating the eb... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

    def wait_create_rds_cluster(self, cluster_identifier):
        cmd = ['rds', 'describe-db-clusters']
        cmd += ['--db-cluster-identifier', cluster_identifier]

        elapsed_time = 0
        while True:
            result = self.run(cmd)

            # noinspection PyBroadException
            try:
                for db_cluster in result['DBClusters']:
                    db_cluster = dict(db_cluster)

                    if db_cluster['Status'] == 'available':
                        return
            except Exception:
                pass

            print('waiting for a new cluster is ready... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

            if elapsed_time > 60 * 30:
                raise Exception()

    def wait_create_nat_gateway(self, eb_vpc_id=None):
        cmd = ['ec2', 'describe-nat-gateways']

        elapsed_time = 0
        while True:
            result = self.run(cmd)
            count = 0
            for r in result['NatGateways']:
                if eb_vpc_id and r.get('VpcId') != eb_vpc_id:
                    continue
                if r.get('State') != 'available':
                    count += 1

            if count == 0:
                break

            print('waiting for a new nat gateway... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

    def wait_delete_nat_gateway(self, eb_vpc_id=None):
        cmd = ['ec2', 'describe-nat-gateways']

        elapsed_time = 0
        while True:
            result = self.run(cmd)
            count = 0
            for r in result['NatGateways']:
                if eb_vpc_id and r.get('VpcId') != eb_vpc_id:
                    continue
                if r.get('State') != 'deleted':
                    count += 1

            if count == 0:
                break

            print('deleting the nat gateway... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

    def get_eb_gendo_windows_platform(self, target_service):
        in_use_eb_windows_version = '2.19.2'

        if target_service == 'elastic_beanstalk':
            return f'64bit Windows Server 2016 v{in_use_eb_windows_version} running IIS 10.0'

        if target_service == 'imagebuilder':
            return f'IIS 10.0 running on 64bit Windows Server 2016/{in_use_eb_windows_version}'

        raise Exception(f'unsupported platform: {target_service}')


def parse_args(require_arg=False):
    if require_arg:
        usage = 'usage: %prog [options] arg'
    else:
        usage = 'usage: %prog [options]'

    parser = OptionParser(usage=usage)
    parser.add_option('-f', '--force', action='store_true', help='skip the phase confirm')
    parser.add_option('-b', '--branch', help='override git branch')
    parser.add_option('-r', '--region', help='filter for specific aws region')
    (options, args) = parser.parse_args(sys.argv)

    if not options.force:
        _confirm_phase()

    option_dict = {k: v for k, v in options.__dict__.items() if v is not None}
    return option_dict, args


def print_message(message):
    print('*' * 80)
    print(message + '\n')


def print_session(message):
    print('\n' + '#' * 80 + '\n' + '#' * 80)
    print('\n\t[ ' + message + ' ]\n\n')


def read_file(file_path):
    f = open(file_path)
    lines = list()
    for ll in f.readlines():
        lines.append(ll)
    f.close()

    return lines


def write_file(file_path, lines):
    f = open(file_path, 'w')
    for ll in lines:
        f.write(ll)
    f.close()


def re_sub_lines(lines, pattern, repl):
    new_lines = list()
    for ll in lines:
        ll = re.sub(pattern, repl, ll)
        new_lines.append(ll)

    return new_lines


def reset_template_dir(options):
    template_name = env['template']['NAME']
    print_session('reset template: %s' % template_name)

    if not os.path.exists('template/'):
        subprocess.Popen(['mkdir', '-p', './template']).communicate()

    git_url = env['template']['GIT_URL']
    name = env['template']['NAME']
    phase = env['common']['PHASE']

    print_message('cleanup existing template')

    subprocess.Popen(['rm', '-rf', './%s' % name], cwd='template').communicate()

    print_message('download template from git repository')
    branch = options.get('branch', 'master' if phase == 'dv' else phase)
    print(f'branch: {branch}')
    template_git_command = ['git', 'clone', '--depth=1', '-b', branch, git_url]
    subprocess.Popen(template_git_command, cwd='template').communicate()

    if not os.path.exists('template/' + name):
        raise Exception()


def remove_kaji_in_template_dir():
    if not os.path.exists('template/'):
        subprocess.Popen(['mkdir', '-p', './template']).communicate()

    print_session('remove kaji in template')

    subprocess.Popen(['rm', '-rf', './kaji'], cwd='template').communicate()

    if not os.path.exists('template/'):
        raise Exception()
