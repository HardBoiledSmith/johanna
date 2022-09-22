# !/usr/bin/env python3

import json
import subprocess
import sys
import time

from datetime import datetime
from optparse import OptionParser

from env import env
from run_common import AWSCli, _confirm_phase
from run_common import print_session
from run_common import print_message
from run_common import reset_template_dir


def parse_args():
    parser = OptionParser()
    parser.add_option('-f', '--force', action='store_true', help='skip the phase confirm')
    parser.add_option('-b', '--branch', help='override git branch')
    parser.add_option('-r', '--region', help='filter for specific aws region')
    parser.add_option('-t', '--target', help='target on-premises instances which are seperated by semi-colon')
    (options, args) = parser.parse_args(sys.argv)

    if not options.force:
        _confirm_phase()

    option_dict = {k: v for k, v in options.__dict__.items() if v is not None}
    return option_dict, args


options, args = parse_args()

print_session('Create ramiel partial deployment')

reset_template_dir(options)

phase = env['common']['PHASE']
branch = options.get('branch', 'master' if phase == 'dv' else phase)
target_name = f'{phase}_create_ramiel_full_deployment'
region = 'ap-northeast-2'
if phase not in ['qa', 'op']:
    raise Exception(f'Invalid branch: {phase}')

settings = None
for ss in env.get('codebuild', list()):
    settings = ss
    if target_name and ss['NAME'] != target_name:
        continue

    assert ss['AWS_REGION'] == 'ap-northeast-2'
    if region and ss['AWS_REGION'] != region:
        continue
if not settings:
    raise Exception('settings is required')

aws_cli = AWSCli(region)

cc = [
    'deploy', 'list-on-premises-instances',
    '--query', 'instanceNames', '--output', 'json',
]
ll = aws_cli.run(cc)

print(f'Target instances ({len(ll)} servers):')
print_message(*ll)

target = options.get('target')
if not target:
    raise Exception('target is required')
tt = target.split(';')
cc = set(ll) - set(tt)
if cc:
    raise Exception(f'invalid target is included: {cc}')

cc = [
    'curl',
    'https://hbsmith-codebuild-artifacts-ap-northeast-2-20210609.s3.ap-northeast-2.amazonaws.com'
    f'/ramiel/{phase}-artifact.txt',
]
_p = subprocess.Popen(cc, stdout=subprocess.PIPE, cwd='/tmp')
pp = _p.communicate()
if _p.returncode != 0:
    raise Exception('failed to get artifact file')
artifact = pp[0]

print_message('Cleaning up the instance tagging(s)')
cc = list()
cc.extend(['deploy', 'remove-tags-from-on-premises-instances'])
cc.append('--instance-names')
cc.extend(ll)
cc.extend(['--tags', 'Key=PartialDeployment'])
aws_cli.run(cc)

app_name = f'{phase}_ramiel_app'
deployment_group = f'{phase}_ramiel_partial_deployment_group'
s3_location = f'''{{
    "bucket": "hbsmith-codebuild-artifacts-ap-northeast-2-20210609",
    "key": "ramiel/{artifact}",
    "bundleType": "zip"
}}'''

print('-' * 80)
print(f'\tAPP_NAME          : {app_name}')
print(f'\tDEPLOYMENT_GROUP  : {deployment_group}')
print('-' * 80)

print_message(f'Tagging the target instances: {tt}')
cc = list()
cc.extend(['deploy', 'add-tags-to-on-premises-instances'])
cc.append('--instance-names')
cc.extend(tt)
cc.extend(['--tags', 'Key=PartialDeployment'])
aws_cli.run(cc)

cc = [
    'deploy', 'create-deployment',
    '--application-name', app_name,
    '--deployment-group-name', deployment_group,
    '--s3-location', s3_location,
]
rr = aws_cli.run(cc)

deployment_id = rr['deploymentId']
start_time = datetime.now()
cc = [
    'deploy', 'get-deployment',
    '--deployment-id', deployment_id,
    '--query', 'deploymentInfo.status',
    '--output', 'text',
]
ss = 'InProgress'
while ss not in ('Succeeded', 'Failed'):
    ss = aws_cli.run(cc)
    ss = ss.strip()
    print(f'Deployment status: {ss} (Elapsed: {(datetime.now() - start_time).seconds}s)')
    time.sleep(10)

cc = [
    'deploy', 'get-deployment',
    '--deployment-id', deployment_id,
    '--query', 'deploymentInfo.deploymentOverview',
    '--output', 'json',
]
rr = aws_cli.run(cc)
rr = json.dumps(rr, indent=4, sort_keys=True)
print(rr)
