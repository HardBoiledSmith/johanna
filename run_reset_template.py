#!/usr/bin/env python3
import os
import subprocess

from env import env
from run_common import print_message
from run_common import print_session

template_name = env['template']['NAME']
print_session('reset template dir: %s' % template_name)

print_message('cleanup existing template')

if os.path.exists('./template'):
    subprocess.Popen(['rm', '-rf', 'template/']).communicate()

subprocess.Popen(['mkdir', '-p', './template']).communicate()

if not os.path.exists('./template'):
    raise Exception()
