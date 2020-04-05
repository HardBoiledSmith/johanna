#!/usr/bin/env python3

from time import sleep

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session


def terminate_iam_for_appstream():
    aws_cli = AWSCli()
    role_name = 'AmazonAppStreamServiceAccess'
    print_message('delete iam role')

    # noinspection PyShadowingNames
    cc = ['iam', 'detach-role-policy']
    cc += ['--role-name', role_name]
    cc += ['--policy-arn', 'arn:aws:iam::aws:policy/service-role/AmazonAppStreamServiceAccess']
    aws_cli.run(cc, ignore_error=True)

    # noinspection PyShadowingNames
    cc = ['iam', 'delete-role']
    cc += ['--role-name', role_name]
    aws_cli.run(cc, ignore_error=True)

    role_name = 'ApplicationAutoScalingForAmazonAppStreamAccess'
    # noinspection PyShadowingNames
    cc = ['iam', 'detach-role-policy']
    cc += ['--role-name', role_name]
    cc += ['--policy-arn', 'arn:aws:iam::aws:policy/service-role/ApplicationAutoScalingForAmazonAppStreamAccess']
    aws_cli.run(cc, ignore_error=True)

    # noinspection PyShadowingNames
    cc = ['iam', 'delete-role']
    cc += ['--role-name', role_name]
    aws_cli.run(cc, ignore_error=True)


def stop_fleet(fleet_name):
    aws_cli = AWSCli()
    cmd = ['appstream', 'stop-fleet']
    cmd += ['--name', fleet_name]
    aws_cli.run(cmd, ignore_error=True)


def delete_fleet(fleet_name):
    aws_cli = AWSCli()
    cmd = ['appstream', 'delete-fleet']
    cmd += ['--name', fleet_name]
    return aws_cli.run(cmd, ignore_error=True)


def delete_stack(stack_name):
    aws_cli = AWSCli()
    cmd = ['appstream', 'delete-stack']
    cmd += ['--name', stack_name]
    return aws_cli.run(cmd, ignore_error=True)


def disassociate_fleet(fleet_name, stack_name):
    aws_cli = AWSCli()
    cmd = ['appstream', 'disassociate-fleet']
    cmd += ['--fleet-name', fleet_name]
    cmd += ['--stack-name', stack_name]

    rr = aws_cli.run(cmd, ignore_error=True)
    return bool(rr)


def wait_state(name):
    aws_cli = AWSCli()
    elapsed_time = 0
    is_waiting = True

    while is_waiting:
        cmd = ['appstream', 'describe-fleets']
        cmd += ['--name', name]
        rr = aws_cli.run(cmd)

        for r in rr['Fleets']:
            if 'STOPPED' == r['State']:
                is_waiting = False

        if elapsed_time > 1200:
            raise Exception('timeout: terminating fleet (%s)' % name)

        sleep(5)
        print('waiting for fleet terminated... (elapsed time: \'%d\' seconds)' % elapsed_time)
        elapsed_time += 5


################################################################################
#
# start
#
################################################################################


if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()

    target_name = None

    if len(args) > 1:
        target_name = args[1]

    print_session('terminate appstream stack & fleet')

    for env_s in env['appstream']['STACK']:
        if target_name and env_s['NAME'] != target_name:
            continue

        stack_name = env_s['NAME']
        fleet_name = env_s['FLEET_NAME']
        image_name = env_s['IMAGE_NAME']

        disassociate_fleet(fleet_name, stack_name)
        delete_stack(stack_name)
        stop_fleet(fleet_name)
        wait_state(fleet_name)
        delete_fleet(fleet_name)

    terminate_iam_for_appstream()
