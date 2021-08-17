#!/usr/bin/env python3
from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_terminate_image(name):
    aws_cli = AWSCli()

    print_message(f'terminate imagebuilder {name} ami')

    cmd = ['imagebuilder', 'list-images']
    rr = aws_cli.run(cmd)

    if not rr:
        return

    ami_arn_list = list()
    for r in rr['imageVersionList']:
        ami_arn_list.append(r['arn'])

    for ami_arn in ami_arn_list:
        cmd = ['imagebuilder', 'list-image-build-versions']
        cmd += ['--image-version-arn', ami_arn]
        rr = aws_cli.run(cmd)
        for r in rr['imageSummaryList']:
            cmd = ['imagebuilder', 'list-image-build-versions']
            cmd += ['--image-version-arn', ami_arn]
            arn_version_list = aws_cli.run(cmd, ignore_error=True)
            if arn_version_list['imageSummaryList']:
                cmd = ['imagebuilder', 'delete-image']
                cmd += ['--image-build-version-arn', r['arn']]
                aws_cli.run(cmd, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate imagebuilder')

target_name = None
region = options.get('region')
is_target_exists = False

if len(args) > 1:
    target_name = args[1]

name = 'gendo'
run_terminate_image(name)

# for settings in eb.get('ENVIRONMENTS', list()):
#     if target_name and settings['NAME'] != target_name:
#         continue
#
#     if region and settings['AWS_REGION'] != region:
#         continue
#
#     is_target_exists = True
#
#
#     terminate_iam_profile_for_ec2_instances(settings['NAME'])
#
# if is_target_exists is False:
#     mm = list()
#     if target_name:
#         mm.append(target_name)
#     if region:
#         mm.append(region)
#     mm = ' in '.join(mm)
#     print(f'eb environment: {mm} is not found in config.json')
