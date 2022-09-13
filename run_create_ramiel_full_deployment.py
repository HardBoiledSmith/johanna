#!/usr/bin/env python3

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

print_session('Create ramiel full deployment')

reset_template_dir(options)

phase = env['common']['PHASE']
branch = options.get('branch', 'master' if phase == 'dv' else phase)
# TODO: test
branch = 'op'
#
if branch not in ['qa', 'op']:
    raise Exception(f'Invalid branch: {branch}')
settings = env['codebuild'][f'{branch}_create_ramiel_full_deployment']
region = settings['AWS_REGION']

aws_cli = AWSCli(region)

cc = [
    'deploy', 'list-on-premises-instances',
    '--query', 'instanceNames', '--output', 'json',
]
rr = aws_cli.run(cc)

print(f'Target instances ({len(rr)} servers):')
print_message(rr)

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

app_name = f'{phase}_ramiel_app'
deployment_group = f'{phase}_ramiel_deployment_group'
s3_location = f'''{{
    "bucket": "hbsmith-codebuild-artifacts-ap-northeast-2-20210609",
    "key": "ramiel/{artifact}",
    "bundleType": "zip"
}}'''

print('-' * 80)
print(f'\tAPP_NAME          : {app_name}')
print(f'\tDEPLOYMENT_GROUP  : {deployment_group}')
print('-' * 80)

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
ss = None
while not ss and ss != 'Succeeded' and ss != 'Failed':
    ss = aws_cli.run(cc)
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
