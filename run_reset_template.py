#!/usr/bin/env python3
import os
import subprocess

from env import env
from run_common import print_message
from run_common import print_session

template_name = env['template']['NAME']
print_session('reset template dir: %s' % template_name)

print_message('cleanup existing template')

if os.path.exists('template/'):
    subprocess.Popen(['rm', '-rf', './template'], cwd='template').communicate()

subprocess.Popen(['mkdir', '-p', './template']).communicate()

git_url = env['template']['GIT_URL']
name = env['template']['NAME']
phase = env['common']['PHASE']

print_message('download template from git repository')

if phase == 'dv':
    template_git_command = ['git', 'clone', '--depth=1', git_url]
else:
    template_git_command = ['git', 'clone', '--depth=1', '-b', phase, git_url]

subprocess.Popen(template_git_command, cwd='template').communicate()

if not os.path.exists('template/' + name):
    raise Exception()
