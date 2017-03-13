#!/usr/bin/env python3
import os
import subprocess

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

aws_cli = AWSCli()

template_name = env['template']['NAME']
print_session('reset template: %s' % template_name)

git_url = env['template']['GIT_URL']
name = env['template']['NAME']
phase = env['common']['PHASE']

print_message('cleanup existing template')

subprocess.Popen(['mkdir', '-p', './template']).communicate()
subprocess.Popen(['rm', '-rf', './%s' % name], cwd='template').communicate()

print_message('download template from git repository')
if phase == 'dv':
    template_git_command = ['git', 'clone', '--depth=1', git_url]
else:
    template_git_command = ['git', 'clone', '--depth=1', '-b', phase, git_url]
subprocess.Popen(template_git_command, cwd='template').communicate()

if not os.path.exists('template/' + name):
    raise Exception()
