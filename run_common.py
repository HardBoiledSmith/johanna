#!/usr/bin/env python3
from __future__ import print_function

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
    eb = env['elasticbeanstalk']
    print('Your current environment values are below')
    print('-' * 80)
    print('\tPHASE               : \'%s\'' % phase)
    for eb_env in eb['ENVIRONMENTS']:
        print('\tCNAME of %-10s : \'%s\'' % (eb_env['NAME'], eb_env['CNAME']))
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
    cidr_subnet['eb'] = dict()
    cidr_subnet['eb']['private_1'] = env['common']['AWS_SUBNET_EB_PRIVATE_1']
    cidr_subnet['eb']['private_2'] = env['common']['AWS_SUBNET_EB_PRIVATE_2']
    cidr_subnet['eb']['public_1'] = env['common']['AWS_SUBNET_EB_PUBLIC_1']
    cidr_subnet['eb']['public_2'] = env['common']['AWS_SUBNET_EB_PUBLIC_2']

    def __init__(self):
        if not env['aws'].get('AWS_ACCESS_KEY_ID') or \
                not env['aws'].get('AWS_SECRET_ACCESS_KEY') or \
                not env['aws'].get('AWS_DEFAULT_REGION'):
            raise Exception()

        self.env = dict(os.environ)
        self.env['AWS_ACCESS_KEY_ID'] = env['aws']['AWS_ACCESS_KEY_ID']
        self.env['AWS_SECRET_ACCESS_KEY'] = env['aws']['AWS_SECRET_ACCESS_KEY']
        self.env['AWS_DEFAULT_REGION'] = env['aws']['AWS_DEFAULT_REGION']

    def _run(self, args, cwd=None, ignore_error=None):
        if ignore_error:
            print('\n>> command(ignore error):', end=" ")
        else:
            print('\n>> command:', end=" ")
        print(' '.join(args))
        result, error = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         cwd=cwd, env=self.env).communicate()
        # noinspection PyUnresolvedReferences
        result = result.decode('utf-8')

        if error:
            print(error)
            if not ignore_error:
                raise Exception()

        if args[0] == 'aws':
            # noinspection PyBroadException
            try:
                return json.loads(result)
            except:
                return result
        elif args[0] == 'eb':
            return result

        return dict()

    def run(self, args, cwd=None, ignore_error=None):
        args = ['aws'] + args
        return self._run(args, cwd, ignore_error)

    def run_eb(self, args, cwd=None, ignore_error=None):
        args = ['eb'] + args
        return self._run(args, cwd, ignore_error)

    def get_vpc_id(self):
        rds_vpc_id = None
        cmd = ['ec2', 'describe-vpcs']
        cmd += ['--filters=Name=cidr,Values=%s' % self.cidr_vpc['rds']]
        result = self.run(cmd)
        if len(result['Vpcs']) == 1:
            rds_vpc_id = dict(result['Vpcs'][0])['VpcId']

        eb_vpc_id = None
        cmd = ['ec2', 'describe-vpcs']
        cmd += ['--filters=Name=cidr,Values=%s' % self.cidr_vpc['eb']]
        result = self.run(cmd)
        if len(result['Vpcs']) == 1:
            eb_vpc_id = dict(result['Vpcs'][0])['VpcId']

        return rds_vpc_id, eb_vpc_id

    def get_elasticache_address(self):
        cmd = ['elasticache', 'describe-cache-clusters', '--show-cache-node-info']

        elapsed_time = 0
        cache_address = None
        while not cache_address:
            result = self.run(cmd)

            # noinspection PyBroadException
            try:
                cache_clusters = result['CacheClusters'][0]
                cache_nodes = dict(cache_clusters)['CacheNodes'][0]
                cache_endpoint = dict(cache_nodes)['Endpoint']
                cache_address = dict(cache_endpoint)['Address']
                if cache_address:
                    return cache_address
            except:
                pass

            print('waiting for a new cache... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

            if elapsed_time > 60 * 30:
                raise Exception()

    def get_rds_address(self, read_replica=None):
        cmd = ['rds', 'describe-db-instances']

        elapsed_time = 0
        db_address = None
        while not db_address:
            result = self.run(cmd)

            # noinspection PyBroadException
            try:
                for db_instance in result['DBInstances']:
                    db_instance = dict(db_instance)

                    if not read_replica and 'ReadReplicaSourceDBInstanceIdentifier' in db_instance:
                        continue
                    elif read_replica and 'ReadReplicaSourceDBInstanceIdentifier' not in db_instance:
                        continue

                    db_endpoint = db_instance['Endpoint']
                    db_address = dict(db_endpoint)['Address']

                    if db_address:
                        return db_address
            except:
                pass

            print('waiting for a new database... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5

            if elapsed_time > 60 * 30:
                raise Exception()

    def set_name_tag(self, resource_id, name):
        cmd = ['ec2', 'create-tags']
        cmd += ['--resources', resource_id]
        cmd += ['--tags', 'Key=Name,Value=%s' % name]
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

    def wait_delete_nat_gateway(self):
        cmd = ['ec2', 'describe-nat-gateways']

        elapsed_time = 0
        while True:
            result = self.run(cmd)
            count = 0
            for r in result['NatGateways']:
                if r.get('State') != 'deleted':
                    count += 1

            if count == 0:
                break

            print('deleting the nat gateway... (elapsed time: \'%d\' seconds)' % elapsed_time)
            time.sleep(5)
            elapsed_time += 5


def parse_args(require_arg=False):
    if require_arg:
        usage = 'usage: %prog [options] arg'
    else:
        usage = 'usage: %prog [options]'

    parser = OptionParser(usage=usage)
    parser.add_option("-f", "--force", action="store_true", help='skip the phase confirm')
    (options, args) = parser.parse_args(sys.argv)

    if not options.force:
        _confirm_phase()

    return args


def print_message(message):
    print('*' * 80)
    print(message + '\n')


def print_session(message):
    print('#' * 80 + '\n' + '#' * 80)
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


def download_template():
    git_url = env['template']['GIT_URL']
    name = env['template']['NAME']
    phase = env['common']['PHASE']

    print_session('download ' + name)

    subprocess.Popen(['mkdir', '-p', './template']).communicate()
    subprocess.Popen(['rm', '-rf', './' + name], cwd='template').communicate()
    if phase == 'dv':
        template_git_command = ['git', 'clone', '--depth=1', git_url]
    else:
        template_git_command = ['git', 'clone', '--depth=1', '-b', phase, git_url]
    subprocess.Popen(template_git_command, cwd='template').communicate()

    if not os.path.exists('template/' + name):
        raise Exception()
