#!/usr/bin/env python3
import re
import subprocess
from subprocess import PIPE

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

aws_cli = AWSCli()

print_session('dump mysql schema')

engine = env['rds']['ENGINE']
if engine not in ('mysql', 'aurora'):
    print('not supported:', engine)
    raise Exception()

print_message('get database address')

db_host = 'dv-database.hbsmith.io'
answer = 'no'
if env['common']['PHASE'] == 'dv':
    answer = input('Do you use a database of Vagrant VM? (yes/no): ')
if answer != 'yes':
    db_host = aws_cli.get_rds_address(read_replica=True)

db_user = env['rds']['USER_NAME']
db_password = env['rds']['USER_PASSWORD']
database = env['rds']['DATABASE']
template_name = env['template']['NAME']

print_message('dump schema')

cmd = ['mysqldump']
cmd += ['-h' + db_host]
cmd += ['-u' + db_user]
cmd += ['-p' + db_password]
cmd += ['--comments']
cmd += ['--databases', database]
cmd += ['--ignore-table=%s.django_migrations' % database]
cmd += ['--no-data']

data = subprocess.Popen(cmd, stdout=PIPE).communicate()[0].decode()
line = data.split('\n')
filename = 'template/%s/rds/mysql_schema.sql' % template_name
with open(filename, 'w') as f:
    for ll in line:
        ll = re.sub('^-- MySQL dump.*$', '', ll)
        ll = re.sub('^-- Host.*$', '', ll)
        ll = re.sub('^-- Server version.*$', '', ll)
        ll = re.sub(' AUTO_INCREMENT=[0-9]*', '', ll)
        ll = re.sub('^-- Dump completed on.*$', '', ll)
        f.write(ll + '\n')
