import sys

from env import env
from run_codebuild_wait_done import run_codebuild_wait_done
from run_create_codebuild_vpc import run_create_codebuild_vpc
from run_terminate_codebuild_vpc import run_terminate_vpc_codebuild

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

if env['common']['PHASE'] != 'op':
    codebuild_env = None
    for dd in env['codebuild']:
        if dd['NAME'] == 'reset_database':
            codebuild_env = dd
    if codebuild_env is None:
        print('reset_database env is not exist')
        sys.exit(1)

    run_create_codebuild_vpc('reset_database', codebuild_env)
    is_success = run_codebuild_wait_done('reset_database', env['common']['PHASE'])
    run_terminate_vpc_codebuild('reset_database')
    if not is_success:
        print('fail reset database')
        sys.exit(1)
