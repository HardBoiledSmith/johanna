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

print_message('get database address')

db_host = aws_cli.get_database_address(read_replica=True)
db_user = env['rds']['USER_NAME']
db_password = env['rds']['USER_PASSWORD']
database = env['rds']['DATABASE']

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
for l in line:
    l = re.sub('^-- MySQL dump.*$', '', l)
    l = re.sub('^-- Host.*$', '', l)
    l = re.sub('^-- Server version.*$', '', l)
    l = re.sub(' AUTO_INCREMENT=[0-9]*', '', l)
    l = re.sub('^-- Dump completed on.*$', '', l)
    print(l)
