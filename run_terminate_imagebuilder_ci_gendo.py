#!/usr/bin/env python3

from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def filter_ci_gendo_arn_list(target_resouce_list):
    arn_list = list()
    for r in target_resouce_list:
        if r['name'] and r['name'].startswith('ci_gendo_'):
            arn_list.append(r['arn'])

    return arn_list


def run_terminate_image(name):
    aws_cli = AWSCli()

    account_id = aws_cli.get_caller_account_id()

    print_message(f'delete imagebuilder {name} ami')
    cmd = ['imagebuilder', 'list-images']
    rr = aws_cli.run(cmd)

    ami_arn_list = filter_ci_gendo_arn_list(rr['imageVersionList'])
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
    cmd += ['--filters=Name=name,Values="ci_Gendo*"']
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

    pipe_line_list = filter_ci_gendo_arn_list(rr['imagePipelineList'])
    for pipe_line in pipe_line_list:
        cmd = ['imagebuilder', 'delete-image-pipeline']
        cmd += ['--image-pipeline-arn', pipe_line]
        aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} distributions')
    cmd = ['imagebuilder', 'list-distribution-configurations']
    rr = aws_cli.run(cmd)

    distribution_list = filter_ci_gendo_arn_list(rr['distributionConfigurationSummaryList'])
    for distribution in distribution_list:
        cmd = ['imagebuilder', 'delete-distribution-configuration']
        cmd += ['--distribution-configuration-arn', distribution]
        aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} infrastructures')
    cmd = ['imagebuilder', 'list-infrastructure-configurations']
    rr = aws_cli.run(cmd)

    infrastructure_list = filter_ci_gendo_arn_list(rr['infrastructureConfigurationSummaryList'])
    for infrastructure in infrastructure_list:
        cmd = ['imagebuilder', 'delete-infrastructure-configuration']
        cmd += ['--infrastructure-configuration-arn', infrastructure]
        aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} image-recipes')
    cmd = ['imagebuilder', 'list-image-recipes']
    rr = aws_cli.run(cmd)

    image_recipe_list = filter_ci_gendo_arn_list(rr['imageRecipeSummaryList'])
    for image_recipe in image_recipe_list:
        cmd = ['imagebuilder', 'delete-image-recipe']
        cmd += ['--image-recipe-arn', image_recipe]
        aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} components')

    cmd = ['imagebuilder', 'list-components']
    rr = aws_cli.run(cmd)

    component_list = filter_ci_gendo_arn_list(rr['componentVersionList'])
    for component_arn in component_list:
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

    print_message('delete cloudwatch image builder logs')
    cmd = ['logs', 'describe-log-groups']
    cmd += ['--log-group-name-prefix', '/aws/imagebuilder/ci_gendo']
    rr = aws_cli.run(cmd, ignore_error=True)
    for log_group in rr['logGroups']:
        cmd = ['logs', 'delete-log-group']
        cmd += ['--log-group-name', log_group['logGroupName']]
        aws_cli.run(cmd, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate imagebuilder ci gendo')

name = 'gendo'
run_terminate_image(name)
