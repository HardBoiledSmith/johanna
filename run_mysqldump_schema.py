#!/usr/bin/env python3
import os
import re
import subprocess
from subprocess import PIPE

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session


def _manual_backup():
    aws_cli = AWSCli()

    ################################################################################
    print_session('dump mysql schema')

    engine = env['rds']['ENGINE']
    if engine not in ('aurora', 'aurora-mysql', 'aurora-postgresql'):
        print('not supported:', engine)
        raise Exception()

    ################################################################################
    print_message('get database address')

    if env['common']['PHASE'] != 'dv':
        host = aws_cli.get_rds_address(read_replica=True)
    else:
        while True:
            answer = input('Do you use a database of Vagrant VM? (yes/no): ')
            if answer.lower() == 'no':
                host = aws_cli.get_rds_address(read_replica=True)
                break
            if answer.lower() == 'yes':
                host = 'dv-database.hbsmith.io'
                break

    database = env['rds']['DATABASE']
    password = env['rds']['USER_PASSWORD']
    user = env['rds']['USER_NAME']

    print_message('git clone')

    git_url = env['rds']['GIT_URL']
    mm = re.match(r'^.+/(.+)\.git$', git_url)
    if not mm:
        raise Exception()

    git_folder_name = mm.group(1)
    template_path = 'template/%s' % git_folder_name
    subprocess.Popen(['rm', '-rf', template_path]).communicate()
    subprocess.Popen(['mkdir', '-p', template_path]).communicate()

    git_command = ['git', 'clone', '--depth=1', git_url]

    subprocess.Popen(git_command, cwd='./template').communicate()
    if not os.path.exists(template_path):
        raise Exception()

    _mysql_dump(host, user, password, database, '%s/rds/mysql_schema.sql' % template_path)


def _mysql_dump(host, user, password, database, filename_path):
    ################################################################################
    print_message('dump schema')

    cmd = ['mysqldump']
    cmd += ['-h' + host]
    cmd += ['-u' + user]
    cmd += ['-p' + password]
    cmd += ['--column-statistics=0']
    cmd += ['--comments']
    cmd += ['--databases', database]
    cmd += ['--ignore-table=%s.django_migrations' % database]
    cmd += ['--no-data']

    print('\n>>> ' + ' '.join(cmd) + '\n')

    filename_path_raw = filename_path + '.raw'

    with open(filename_path_raw, 'w') as ff:
        subprocess.Popen(cmd, stdout=ff).communicate()

    with open(filename_path_raw, 'r') as ff_raw, open(filename_path, 'w') as ff:
        while True:
            line = ff_raw.readline()
            if not line:
                break

            if line.startswith('-- MySQL dump') or \
                    line.startswith('-- Host') or \
                    line.startswith('-- Server version') or \
                    line.startswith('-- Dump completed on'):
                ff.write('\n')
                continue

            line = re.sub(' AUTO_INCREMENT=[0-9]*', '', line)
            ff.write(line)

    cmd = ['rm', filename_path_raw]

    subprocess.Popen(cmd, stdout=PIPE).communicate()


################################################################################
#
# start
#
################################################################################
print_session('mysqldump data')

################################################################################
if __name__ != "__main__":
    _manual_backup()
