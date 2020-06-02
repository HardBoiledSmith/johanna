#!/usr/bin/env python3
import json
import sys
from time import sleep

from run_common import AWSCli


def wait_build_done(name, build_id):
    aws_cli = AWSCli()

    elapsed_time = 0
    is_waiting = True
    while is_waiting:
        cmd = ['codebuild', 'batch-get-builds']
        cmd += ['--ids', build_id]
        rr = aws_cli.run(cmd)
        rr = rr['builds'][0]

        if rr['currentPhase'] == 'COMPLETED':
            return

        print(json.dumps(rr['phases'][-1], indent=2))

        if elapsed_time > 1200:
            raise Exception(f'timeout: wait build done ({name})')

        sleep(5)
        print('wait wait build done... (elapsed time: \'%d\' seconds)' % elapsed_time)
        elapsed_time += 5


def get_build_id(name):
    aws_cli = AWSCli()

    cmd = ['codebuild', 'list-builds-for-project']
    cmd += ['--project-name', name]
    rr = aws_cli.run(cmd)
    build_id = rr['ids'][0]
    return build_id


def is_success(build_id):
    aws_cli = AWSCli()

    cmd = ['codebuild', 'batch-get-builds']
    cmd += ['--ids', build_id]
    rr = aws_cli.run(cmd)

    ss = rr['builds'][0]['buildStatus']
    print(f'BuildStatus : {ss}')

    if ss == 'SUCCEEDED':
        return True
    else:
        return False


def start_codebuild(name, phase=None):
    aws_cli = AWSCli()
    cmd = ['codebuild', 'start-build']
    cmd += ['--project-name', name]
    if phase:
        cmd += ['--source-version', phase]

    rr = aws_cli.run(cmd)
    return rr['build']['id']


def run_codebuild_wait_done(name, phase):
    ii = start_codebuild(name, phase=phase)
    wait_build_done(name, ii)

    if is_success(ii):
        print(f'{name} is done(SUCCEEDED)')
        sys.exit(0)
    else:
        print(f'{name} is done(FAIL)')
        sys.exit(1)
