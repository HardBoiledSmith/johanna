#!/usr/bin/env python3
import json
import time

from env import env
from run_common import AWSCli
from run_create_codebuild_vpc import run_create_vpc_project
from run_terminate_codebuild import run_terminate_vpc_project


def wait_build_done(aws_cli, name, build_id):
    elapsed_time = 0
    is_waiting = True
    while is_waiting:
        cmd = ['codebuild', 'batch-get-builds']
        cmd += ['--ids', build_id]
        rr = aws_cli.run(cmd)
        rr = rr['builds'][0]

        if rr['buildStatus'] != 'IN_PROGRESS':
            return

        print(json.dumps(rr['phases'][-1], indent=2))

        if elapsed_time > 1200:
            raise Exception(f'timeout: wait build done ({name})')

        time.sleep(5)
        print('wait build done... (elapsed time: \'%d\' seconds)' % elapsed_time)
        elapsed_time += 5


def wait_rds_instance_available(aws_cli):
    elapsed_time = 0
    is_waiting = True

    while is_waiting:
        cmd = ['rds', 'describe-db-instances']
        rr = aws_cli.run(cmd)
        is_available = True

        for r in rr['DBInstances']:
            if r['DBInstanceStatus'] != 'available':
                is_available = False
                break

        if is_available:
            return

        if elapsed_time > 1200:
            raise Exception('timeout: wait rds available')

        time.sleep(5)
        print('wait rds available... (elapsed time: \'%d\' seconds)' % elapsed_time)
        elapsed_time += 5


def get_build_id(aws_cli, name):
    cmd = ['codebuild', 'list-builds-for-project']
    cmd += ['--project-name', name]
    rr = aws_cli.run(cmd)
    build_id = rr['ids'][0]
    return build_id


def is_build_success(aws_cli, build_id):
    cmd = ['codebuild', 'batch-get-builds']
    cmd += ['--ids', build_id]
    rr = aws_cli.run(cmd)

    ss = rr['builds'][0]['buildStatus']
    print(f'BuildStatus : {ss}')

    if ss == 'SUCCEEDED':
        return True
    else:
        return False


def start_codebuild(aws_cli, name, phase=None):
    cmd = ['codebuild', 'start-build']
    cmd += ['--project-name', name]
    if phase:
        cmd += ['--source-version', phase]

    rr = aws_cli.run(cmd)
    return rr['build']['id']


if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

if env['common']['PHASE'] == 'op':
    raise Exception('op is not supported!')

codebuild_env = None
for dd in env['codebuild']:
    if dd['NAME'] == 'reset_database':
        codebuild_env = dd
        break

if codebuild_env is None:
    raise Exception('reset_database is not exist in env')

run_create_vpc_project('reset_database', codebuild_env)

branch = env['common']['PHASE']
if env['common']['PHASE'] == 'dv':
    branch = 'master'

aws_cli = AWSCli()

wait_rds_instance_available(aws_cli)

build_id = start_codebuild(aws_cli, 'reset_database', phase=branch)
wait_build_done(aws_cli, 'reset_database', build_id)

run_terminate_vpc_project('reset_database', codebuild_env)

if not is_build_success(build_id):
    raise Exception('build failed: reset_database')
