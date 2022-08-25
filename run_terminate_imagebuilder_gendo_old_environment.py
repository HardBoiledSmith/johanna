#!/usr/bin/env python3

import re

from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def filter_imagebuilder_resource_arn_list(target_resouce_list):
    arn_list = list()
    for r in target_resouce_list:
        if r['name'] and r['name'].startswith('gendo_'):
            arn_list.append(r['arn'])

    return arn_list


def arn_list_any_imagebuilder_resource(target_arr, timestamp):
    for ll in target_arr:
        if timestamp in ll:
            return True
    return False


def log_list_any_cloudwatch_log(target_arr, timestamp):
    for ll in target_arr:
        if timestamp in ll['logGroupName']:
            return True
    return False


def image_list_any_ec2_image(target_arr, timestamp):
    for img in target_arr:
        for tag in img['Tags']:
            # 태그 순서가 항상 일정하지 않음.
            if tag['Key'] == 'Ec2ImageBuilderArn' and timestamp in tag['Value']:
                return True
    return False


def delete_version_list_any_imagebuilder_resource(delete_versions, arn):
    for vv in delete_versions:
        if vv in arn:
            return True
    return False


def delete_version_list_any_cloudwatch_log(delete_versions, log):
    for vv in delete_versions:
        if vv in log['logGroupName']:
            return True
    return False


def delete_version_list_any_ec2_image(delete_versions, image):
    for vv in delete_versions:
        for tag in image['Tags']:
            # 태그 순서가 항상 일정하지 않음.
            if tag['Key'] == 'Ec2ImageBuilderArn' and vv in tag['Value']:
                print(tag['Value'])
                return True
    return False


def check_exist_resource_version(resource, timestamp):
    if not arn_list_any_imagebuilder_resource(resource['component_list'], timestamp):
        return False

    if not arn_list_any_imagebuilder_resource(resource['ami_arn_list'], timestamp):
        return False

    if not arn_list_any_imagebuilder_resource(resource['image_recipe_list'], timestamp):
        return False

    if not arn_list_any_imagebuilder_resource(resource['distribution_list'], timestamp):
        return False

    if not arn_list_any_imagebuilder_resource(resource['pipe_line_list'], timestamp):
        return False

    if not log_list_any_cloudwatch_log(resource['imagebuilder_cw_log_list'], timestamp):
        return False

    if not image_list_any_ec2_image(resource['ec2_gendo_img_list'], timestamp):
        return False

    return True


def run_terminate_image(name):
    aws_cli = AWSCli()

    account_id = aws_cli.get_caller_account_id()
    imagebuilder_resource = dict()

    # print_message(f'get component list')
    cmd = ['imagebuilder', 'list-components']
    rr = aws_cli.run(cmd)

    component_list = filter_imagebuilder_resource_arn_list(rr['componentVersionList'])

    timestamp_list = list()
    for cc in component_list:
        try:
            found = re.search('-component-(.+?)/', cc).group(1)
            if found:
                timestamp_list.append(found)
        except AttributeError:
            pass
    timestamp_list = set(timestamp_list)

    print_message('get All imagebuilder resouce version')
    cmd = ['imagebuilder', 'list-images']
    rr = aws_cli.run(cmd)
    ami_arn_list = filter_imagebuilder_resource_arn_list(rr['imageVersionList'])

    cmd = ['ec2', 'describe-images']
    cmd += ['--filters=Name=name,Values="Gendo*"']
    cmd += ['--owners', account_id]
    rr = aws_cli.run(cmd)
    ec2_gendo_img_list = rr['Images']

    cmd = ['imagebuilder', 'list-image-pipelines']
    rr = aws_cli.run(cmd)
    pipe_line_list = filter_imagebuilder_resource_arn_list(rr['imagePipelineList'])

    cmd = ['imagebuilder', 'list-distribution-configurations']
    rr = aws_cli.run(cmd)
    distribution_list = filter_imagebuilder_resource_arn_list(rr['distributionConfigurationSummaryList'])

    cmd = ['imagebuilder', 'list-infrastructure-configurations']
    rr = aws_cli.run(cmd)
    infrastructure_list = filter_imagebuilder_resource_arn_list(rr['infrastructureConfigurationSummaryList'])

    cmd = ['imagebuilder', 'list-image-recipes']
    rr = aws_cli.run(cmd)
    image_recipe_list = filter_imagebuilder_resource_arn_list(rr['imageRecipeSummaryList'])

    cmd = ['logs', 'describe-log-groups']
    cmd += ['--log-group-name-prefix', '/aws/imagebuilder/gendo']
    rr = aws_cli.run(cmd, ignore_error=True)
    imagebuilder_cw_log_list = rr['logGroups']

    imagebuilder_resource['imagebuilder_cw_log_list'] = imagebuilder_cw_log_list
    imagebuilder_resource['image_recipe_list'] = image_recipe_list
    imagebuilder_resource['distribution_list'] = distribution_list
    imagebuilder_resource['pipe_line_list'] = pipe_line_list
    imagebuilder_resource['ec2_gendo_img_list'] = ec2_gendo_img_list
    imagebuilder_resource['ami_arn_list'] = ami_arn_list
    imagebuilder_resource['component_list'] = component_list

    normal_resource_version_list = list()
    abnormal_resource_version_list = list()
    for tt in timestamp_list:
        rr = check_exist_resource_version(imagebuilder_resource, tt)
        if rr:
            normal_resource_version_list.append(tt)
        else:
            abnormal_resource_version_list.append(tt)

    delete_version_list = list(abnormal_resource_version_list)
    if len(normal_resource_version_list) > 2:
        normal_resource_version_list.sort(key=int)
        delete_version_list += normal_resource_version_list[2:]

    for ami_arn in ami_arn_list:
        if delete_version_list_any_imagebuilder_resource(delete_version_list, ami_arn):
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
    for img in ec2_gendo_img_list:
        if delete_version_list_any_ec2_image(delete_version_list, img):
            ami = img['ImageId']
            snapshot_id = img['BlockDeviceMappings'][0]['Ebs']['SnapshotId']

            cmd = ['ec2', 'deregister-image']
            cmd += ['--image-id', ami]
            aws_cli.run(cmd)

            cmd = ['ec2', 'delete-snapshot']
            cmd += ['--snapshot-id', snapshot_id]
            aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} pipe lines')
    for pipe_line in pipe_line_list:
        if delete_version_list_any_imagebuilder_resource(delete_version_list, pipe_line):
            cmd = ['imagebuilder', 'delete-image-pipeline']
            cmd += ['--image-pipeline-arn', pipe_line]
            aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} distributions')
    for distribution in distribution_list:
        if delete_version_list_any_imagebuilder_resource(delete_version_list, distribution):
            cmd = ['imagebuilder', 'delete-distribution-configuration']
            cmd += ['--distribution-configuration-arn', distribution]
            aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} infrastructures')
    for infrastructure in infrastructure_list:
        if delete_version_list_any_imagebuilder_resource(delete_version_list, infrastructure):
            cmd = ['imagebuilder', 'delete-infrastructure-configuration']
            cmd += ['--infrastructure-configuration-arn', infrastructure]
            aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} image-recipes')
    for image_recipe in image_recipe_list:
        if delete_version_list_any_imagebuilder_resource(delete_version_list, image_recipe):
            cmd = ['imagebuilder', 'delete-image-recipe']
            cmd += ['--image-recipe-arn', image_recipe]
            aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} components')
    for component in component_list:
        if delete_version_list_any_imagebuilder_resource(delete_version_list, component):
            cmd = ['imagebuilder', 'list-component-build-versions']
            cmd += ['--component-version-arn', component]
            rr = aws_cli.run(cmd)
            for r in rr['componentSummaryList']:
                cmd = ['imagebuilder', 'list-component-build-versions']
                cmd += ['--component-version-arn', component]
                arn_version_list = aws_cli.run(cmd, ignore_error=True)
                if arn_version_list['componentSummaryList']:
                    cmd = ['imagebuilder', 'delete-component']
                    cmd += ['--component-build-version-arn', r['arn']]
                    aws_cli.run(cmd, ignore_error=True)

    print_message('delete cloudwatch image builder logs')
    for log_group in imagebuilder_cw_log_list:
        if delete_version_list_any_cloudwatch_log(delete_version_list, log_group):
            cmd = ['logs', 'delete-log-group']
            cmd += ['--log-group-name', log_group['logGroupName']]
            aws_cli.run(cmd, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate imagebuilder gendo old environment')

name = 'gendo'
run_terminate_image(name)
