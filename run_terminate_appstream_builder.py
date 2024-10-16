#!/usr/bin/env python3.12

from time import sleep

from env import env
from run_common import AWSCli
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


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


def wait_state(name):
    aws_cli = AWSCli()
    elapsed_time = 0
    is_waiting = True

    while is_waiting:
        cmd = ['appstream', 'describe-image-builders']
        cmd += ['--name', name]
        rr = aws_cli.run(cmd)

        for r in rr['ImageBuilders']:
            if 'STOPPED' == r['State']:
                is_waiting = False

        if elapsed_time > 1200:
            raise Exception('timeout: terminating image builder (%s)' % name)

        sleep(5)
        print('wait image builder stopped... (elapsed time: \'%d\' seconds)' % elapsed_time)
        elapsed_time += 5


################################################################################
#
# start
#
################################################################################
print_session('terminate appstream image builder')

appstream = env['appstream']
target_name = None
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

for settings in appstream.get('IMAGE_BUILDS', list()):
    if target_name and settings['NAME'] != target_name:
        continue

    if not exist_image_builder(settings['NAME']):
        continue

    is_target_exists = True

    stop_image_builder(settings['NAME'])
    wait_state(settings['NAME'])
    delete_image_builder(settings['NAME'])

if is_target_exists is False:
    mm = list()
    if target_name:
        mm.append(target_name)
    mm = ' in '.join(mm)
    print(f'appstream image builder: {mm} is not found in config.json')
