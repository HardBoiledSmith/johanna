#!/usr/bin/env python3

from time import sleep

from env import env
from run_common import AWSCli
from run_common import print_message


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


def delete_image(image_name):
    aws_cli = AWSCli()
    cmd = ['appstream', 'delete-image']
    cmd += ['--name', image_name]
    aws_cli.run(cmd, ignore_error=True)


def delete_image_builder(image_build_name):
    aws_cli = AWSCli()
    cmd = ['appstream', 'delete-image-builder']
    cmd += ['--name', image_build_name]
    aws_cli.run(cmd, ignore_error=True)


def stop_image_builder(name):
    aws_cli = AWSCli()
    cmd = ['appstream', 'stop-image-builder']
    cmd += ['--name', name]
    aws_cli.run(cmd, ignore_error=True)


def exist_image_builder(name):
    aws_cli = AWSCli()
    cmd = ['appstream', 'describe-image-builders']
    cmd += ['--name', name]

    rr = aws_cli.run(cmd, ignore_error=True)
    return bool(rr)


def wait_state(service, name, state):
    services = {
        'image-builder': {
            'cmd': 'describe-image-builders',
            'name': 'ImageBuilders'
        },
        'fleet': {
            'cmd': 'describe-fleets',
            'name': 'Fleets'
        }
    }

    if service not in services:
        raise Exception('only allow services(%s)' % ', '.join(services.keys()))

    aws_cli = AWSCli()
    elapsed_time = 0
    is_not_terminate = True
    ss = services[service]

    while is_not_terminate:
        cmd = ['appstream', ss['cmd']]
        cmd += ['--name', name]
        rr = aws_cli.run(cmd)

        for r in rr[ss['name']]:
            if state == r['State']:
                is_not_terminate = False

        if elapsed_time > 1200:
            raise Exception('timeout: stop appstream image builder(%s)' % name)

        sleep(5)
        print('wait image builder state(%s) (elapsed time: \'%d\' seconds)' % (state, elapsed_time))
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

    for env_ib in env['appstream']['IMAGE_BUILDS']:
        image_builder_name = env_ib['NAME']
        if target_name and image_builder_name != target_name:
            continue

        if not exist_image_builder(image_builder_name):
            continue

        stop_image_builder(image_builder_name)
        wait_state('image-builder', image_builder_name, 'STOPPED')
        delete_image_builder(image_builder_name)

    terminate_iam_for_appstream()
