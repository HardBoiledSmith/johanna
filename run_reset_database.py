#!/usr/bin/env python3
import time

from env import env
from run_common import AWSCli
from run_create_codebuild_vpc import run_create_vpc_project
from run_terminate_codebuild_common import run_terminate_vpc_project

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

if env['common']['PHASE'] == 'op':
    raise Exception('op is not supported!')

settings = None
for dd in env['codebuild']:
    if dd['NAME'] == 'reset_database':
        settings = dd
        break

if settings is None:
    raise Exception('reset_database is not exist in env')

aws_cli = AWSCli()

ev = settings['ENV_VARIABLES']

writer_endpoint = aws_cli.get_rds_address(read_replica=False)
ev.append({
    "name": "HOST",
    "value": writer_endpoint,
    "type": "PLAINTEXT"
})

account_id = aws_cli.get_caller_account_id()
ev.append({
    "name": "CANONICAL_ID",
    "value": account_id,
    "type": "PLAINTEXT"
})

run_create_vpc_project('reset_database', settings)

branch = 'master' if env['common']['PHASE'] == 'dv' else env['common']['PHASE']

cmd = ['codebuild', 'start-build']
cmd += ['--project-name', 'reset_database']
cmd += ['--source-version', branch]
result = aws_cli.run(cmd)

build_id = result['build']['id']

last_build_status = ''
elapsed_time = 0
while True:
    cmd = ['codebuild', 'batch-get-builds']
    cmd += ['--ids', build_id]
    rr = aws_cli.run(cmd)
    rr = rr['builds'][0]

    if rr['buildStatus'] != 'IN_PROGRESS':
        last_build_status = rr['buildStatus']
        break

    if elapsed_time > 1200:
        raise Exception('timeout')

    time.sleep(5)
    print('wait build done... (elapsed time: \'%d\' seconds)' % elapsed_time)
    elapsed_time += 5

run_terminate_vpc_project('reset_database', settings)

if last_build_status != 'SUCCEEDED':
    raise Exception('build failed')
