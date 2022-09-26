# !/usr/bin/env python3

import json
import subprocess
import time

from datetime import datetime
from env import env
from run_common import AWSCli
from run_common import print_session
from run_common import print_message
from run_common import reset_template_dir

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()

################################################################################
#
# start
#
################################################################################
print_session('Create codedeploy ramiel deployment')

reset_template_dir(options)

phase = env['common']['PHASE']
branch = options.get('branch', 'master' if phase == 'dv' else phase)
target_name = f'{phase}_create_codedeploy_ramiel'
region = 'ap-northeast-2'

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
all_instances = aws_cli.run(cc)

print(f'Target instances ({len(all_instances)} servers):')
print_message(*all_instances)

partial_deployment = False
target_instances = None
if len(args) > 1:
    tt = args[1]
    tt = tt.replace(' ', '')
    tt = tt.split(';')
    tt = [vv for vv in tt if vv != '']
    if set(tt if tt else []) - set(all_instances):
        raise Exception(f'Invalid instance hostname(s): {tt}')

    partial_deployment = True
    target_instances = tt

if partial_deployment and not target_instances:
    raise Exception('Target instances are required for partial deployment')

cc = [
    'curl',
    'https://hbsmith-codebuild-artifacts-ap-northeast-2-20210609.s3.ap-northeast-2.amazonaws.com'
    f'/ramiel/{branch.lower()}-artifact.txt',
]
_p = subprocess.Popen(cc, stdout=subprocess.PIPE, cwd='/tmp')
pp = _p.communicate()
if _p.returncode != 0:
    raise Exception('failed to get artifact file')
artifact = pp[0].decode()
artifact = artifact.strip()
if artifact[:2] not in ['qa', 'op'] \
        and not artifact.startswith('master') \
        and not artifact.startswith('dev'):
    raise Exception(f'Invalid artifact: {artifact}')

app_name = f'{phase}_ramiel_app'
deployment_group = f'{phase}_ramiel_partial_deployment_group' if partial_deployment \
    else f'{phase}_ramiel_deployment_group'
s3_location = f'''{{
    "bucket": "hbsmith-codebuild-artifacts-ap-northeast-2-20210609",
    "key": "ramiel/{artifact}",
    "bundleType": "zip"
}}'''

print('-' * 80)
print(f'\tAPP_NAME          : {app_name}')
print(f'\tDEPLOYMENT_GROUP  : {deployment_group}')
print('-' * 80)

print_message('Cleaning up the instance tagging(s)')
cc = list()
cc.extend(['deploy', 'remove-tags-from-on-premises-instances'])
cc.append('--instance-names')
cc.extend(all_instances)
cc.extend(['--tags', 'Key=PartialDeployment'])
aws_cli.run(cc)

if partial_deployment:
    print_message(f'Tagging the target instances: {target_instances}')
    cc = list()
    cc.extend(['deploy', 'add-tags-to-on-premises-instances'])
    cc.append('--instance-names')
    cc.extend(target_instances)
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
