#!/usr/bin/env python3
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_terminate_imagebuilder_iam import terminate_iam_profile_for_imagebuilder

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_terminate_image(name):
    aws_cli = AWSCli()

    print_message(f'delete imagebuilder {name} ami')

    account_id = aws_cli.get_caller_account_id()

    cmd = ['imagebuilder', 'list-images']
    rr = aws_cli.run(cmd)

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

    print_message(f'delete ec2 {name} ami and snapshot')

    cmd = ['ec2', 'describe-images']
    cmd += ['--filters=Name=name,Values="Gendo*"']
    cmd += ['--owners', account_id]
    rr = aws_cli.run(cmd)

    for r in rr['Images']:
        ami = r['ImageId']
        snapshot_id = r['BlockDeviceMappings'][0]['Ebs']['SnapshotId']

        cmd = ['ec2', 'deregister-image']
        cmd += ['--image-id', ami]
        aws_cli.run(cmd)

        cmd = ['ec2', 'delete-snapshot']
        cmd += ['--snapshot-id', snapshot_id]
        aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} pipe lines')

    cmd = ['imagebuilder', 'list-image-pipelines']
    rr = aws_cli.run(cmd)

    for r in rr['imagePipelineList']:
        cmd = ['imagebuilder', 'delete-image-pipeline']
        cmd += ['--image-pipeline-arn', r['arn']]
        aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} distributions')

    cmd = ['imagebuilder', 'list-distribution-configurations']
    rr = aws_cli.run(cmd)

    for r in rr['distributionConfigurationSummaryList']:
        cmd = ['imagebuilder', 'delete-distribution-configuration']
        cmd += ['--distribution-configuration-arn', r['arn']]
        aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} infrastructures')

    cmd = ['imagebuilder', 'list-infrastructure-configurations']
    rr = aws_cli.run(cmd)

    for r in rr['infrastructureConfigurationSummaryList']:
        cmd = ['imagebuilder', 'delete-infrastructure-configuration']
        cmd += ['--infrastructure-configuration-arn', r['arn']]
        aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} image-recipes')

    cmd = ['imagebuilder', 'list-image-recipes']
    rr = aws_cli.run(cmd)

    for r in rr['imageRecipeSummaryList']:
        cmd = ['imagebuilder', 'delete-image-recipe']
        cmd += ['--image-recipe-arn', r['arn']]
        aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} components')

    cmd = ['imagebuilder', 'list-components']
    rr = aws_cli.run(cmd)

    component_arn_list = list()
    for r in rr['componentVersionList']:
        component_arn_list.append(r['arn'])

    for component_arn in component_arn_list:
        cmd = ['imagebuilder', 'list-component-build-versions']
        cmd += ['--component-version-arn', component_arn]
        rr = aws_cli.run(cmd)
        for r in rr['componentSummaryList']:
            cmd = ['imagebuilder', 'list-component-build-versions']
            cmd += ['--component-version-arn', component_arn]
            arn_version_list = aws_cli.run(cmd, ignore_error=True)

            if arn_version_list['componentSummaryList']:
                cmd = ['imagebuilder', 'delete-component']
                cmd += ['--component-build-version-arn', r['arn']]
                aws_cli.run(cmd, ignore_error=True)

    terminate_iam_profile_for_imagebuilder(name)


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
