#!/usr/bin/env python3

import re
import time
from datetime import datetime
from datetime import timedelta
import json

from env import env
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
        # gendo로 시작하는 리소스만 필터링
        if r['name'] and (r['name'].startswith('gendo-') or r['name'].startswith('gendo_')):
            arn_list.append(r['arn'])
    return arn_list


def extract_timestamp_from_name(name):
    """리소스 이름에서 타임스탬프 추출"""
    if not name:
        return None

    # pipeline, distribution, infrastructure
    if name.startswith('gendo-pipeline-') or name.startswith('gendo-distribution-') or name.startswith(
            'gendo-infrastructure-'):
        match = re.search(r'-(\d+)$', name)
        if match:
            return match.group(1)
    # recipe
    elif name.startswith('gendo-recipe-'):
        match = re.search(r'gendo-recipe-(\d+)/', name)
        if match:
            return match.group(1)
    # component
    elif 'component-' in name:
        match = re.search(r'component-(\d+)/', name)
        if match:
            return match.group(1)
    return None


def arn_list_any_imagebuilder_resource(target_arr, timestamp):
    """Image Builder 리소스의 이름에서 타임스탬프를 추출하여 비교"""
    print(f'Checking resource list for timestamp {timestamp}:')
    print(f'Target resource list: {target_arr}')

    for ll in target_arr:
        print(f'Checking resource: {ll}')
        # 리소스 이름에서 타임스탬프 추출
        if 'image-recipe' in ll or 'image_recipe' in ll:
            print(f'Found image recipe: {ll}')
            # gendo-recipe-1748308561 또는 gendo_recipe_1748308561 형식 매칭
            match = re.search(r'gendo[-_]recipe[-_](\d+)', ll)
            if match:
                print(f'Extracted timestamp: {match.group(1)}, comparing with {timestamp}')
                if match.group(1) == timestamp:
                    print(f'Match found for image recipe!')
                    return True
        elif 'component' in ll:
            # gendo-image-provisioning-00-component-1748308561 또는 gendo_image_provisioning_00_component_1748308561 형식 매칭
            match = re.search(r'gendo[-_]image[-_]provisioning[-_]\d+[-_]component[-_](\d+)', ll)
            if match and match.group(1) == timestamp:
                return True
        elif 'image-pipeline' in ll or 'image_pipeline' in ll:
            print(f'Found pipeline: {ll}')
            # gendo-pipeline-1748308561 또는 gendo_pipeline_1748308561 형식 매칭
            match = re.search(r'gendo[-_]pipeline[-_](\d+)', ll)
            if match:
                print(f'Extracted timestamp: {match.group(1)}, comparing with {timestamp}')
                if match.group(1) == timestamp:
                    print(f'Match found for pipeline!')
                    return True
        elif 'distribution-configuration' in ll or 'distribution_configuration' in ll:
            print(f'Found distribution: {ll}')
            # gendo-distribution-1748308561 또는 gendo_distribution_1748308561 형식 매칭
            match = re.search(r'gendo[-_]distribution[-_](\d+)', ll)
            if match:
                print(f'Extracted timestamp: {match.group(1)}, comparing with {timestamp}')
                if match.group(1) == timestamp:
                    print(f'Match found for distribution!')
                    return True
        elif 'infrastructure-configuration' in ll or 'infrastructure_configuration' in ll:
            # gendo-infrastructure-1748308561 또는 gendo_infrastructure_1748308561 형식 매칭
            match = re.search(r'gendo[-_]infrastructure[-_](\d+)', ll)
            if match and match.group(1) == timestamp:
                return True
    print(f'No match found for timestamp {timestamp}')
    return False


def log_list_any_cloudwatch_log(target_arr, timestamp):
    """CloudWatch 로그 그룹 이름에서 타임스탬프를 추출하여 비교"""
    for ll in target_arr:
        log_group_name = ll['logGroupName']
        # 로그 그룹 이름에서 타임스탬프 추출
        name_match = re.search(r'_(\d+)$', log_group_name)
        print('get cw log group name:', name_match)
        if not name_match:
            continue
        resource_timestamp = name_match.group(1)
        if resource_timestamp == timestamp:
            return True
    return False


def image_list_any_ec2_image(target_arr, timestamp):
    """EC2 이미지의 태그에서 타임스탬프를 추출하여 비교"""
    for img in target_arr:
        for tag in img['Tags']:
            if tag['Key'] == 'Ec2ImageBuilderArn':
                # ARN에서 리소스 이름 추출
                match = re.search(r'gendo-recipe-(\d+)', tag['Value'])
                if match and match.group(1) == timestamp:
                    return True
    return False


def delete_version_list_any_imagebuilder_resource(delete_versions, arn):
    """삭제 대상 타임스탬프와 리소스의 타임스탬프를 비교"""
    # image-recipe
    if 'image-recipe' in arn or 'image_recipe' in arn:
        # 타임스탬프 직접 추출 (gendo-recipe-1748308561 또는 gendo_recipe_1748308561)
        match = re.search(r'gendo[-_]recipe[-_](\d+)', arn)
        if match:
            timestamp = match.group(1)
            print(f'extracted recipe timestamp: {timestamp}')
            return timestamp in delete_versions
    # component
    elif 'component' in arn:
        # 타임스탬프 직접 추출 (gendo-image-provisioning-00-component-1748308561 또는 gendo_image_provisioning_00_component_1748308561)
        match = re.search(r'gendo[-_]image[-_]provisioning[-_]\d+[-_]component[-_](\d+)', arn)
        if match:
            timestamp = match.group(1)
            print(f'extracted component timestamp: {timestamp}')
            return timestamp in delete_versions
    # pipeline
    elif 'image-pipeline' in arn or 'image_pipeline' in arn:
        match = re.search(r'gendo[-_]pipeline[-_](\d+)', arn)
        if match:
            timestamp = match.group(1)
            print(f'extracted pipeline timestamp: {timestamp}')
            return timestamp in delete_versions
    # distribution
    elif 'distribution-configuration' in arn or 'distribution_configuration' in arn:
        match = re.search(r'gendo[-_]distribution[-_](\d+)', arn)
        if match:
            timestamp = match.group(1)
            print(f'extracted distribution timestamp: {timestamp}')
            return timestamp in delete_versions
    # infrastructure
    elif 'infrastructure-configuration' in arn or 'infrastructure_configuration' in arn:
        match = re.search(r'gendo[-_]infrastructure[-_](\d+)', arn)
        if match:
            timestamp = match.group(1)
            print(f'extracted infrastructure timestamp: {timestamp}')
            return timestamp in delete_versions
    return False


def delete_version_list_any_ec2_image(delete_versions, image):
    """EC2 이미지의 태그에서 타임스탬프를 추출하여 삭제 대상과 비교"""
    for tag in image['Tags']:
        if tag['Key'] == 'Ec2ImageBuilderArn':
            # ARN에서 리소스 이름 추출
            match = re.search(r'gendo-recipe-(\d+)', tag['Value'])
            if match and match.group(1) in delete_versions:
                return True
    return False


def delete_version_list_any_cloudwatch_log(delete_versions, log):
    """CloudWatch 로그 그룹 이름에서 타임스탬프를 추출하여 삭제 대상과 비교"""
    log_group_name = log['logGroupName']
    # 로그 그룹 이름에서 타임스탬프 추출
    name_match = re.search(r'_(\d+)$', log_group_name)
    print('get cw log group name:', name_match)
    if not name_match:
        return False
    resource_timestamp = name_match.group(1)
    return resource_timestamp in delete_versions


def check_exist_resource_version(resource, timestamp):
    """리소스가 정상적으로 존재하는지 확인"""
    print(f'checking if resource version {timestamp} exists...')

    # 현재 사용 중인 버전은 항상 정상으로 처리
    if timestamp in resource.get('in_use_ami_timestamp_version', []):
        print(f'version {timestamp} is in use')
        return True

    # component 리스트 확인
    component_found = False
    for cc in resource['component_list']:
        print(f'Checking component: {cc}')
        match = re.search(r'gendo-image-provisioning-\d+-component-(\d+)/', cc)
        if match:
            print(f'Found component timestamp: {match.group(1)}, comparing with {timestamp}')
            if match.group(1) == timestamp:
                component_found = True
                print(f'Component match found for version {timestamp}')
                break

    if not component_found:
        print(f'component not found for version {timestamp}')
        return False

    # AMI ARN 리스트 확인
    print(f'Checking AMI ARNs for version {timestamp}:')
    print(f'AMI ARN list: {resource["ami_arn_list"]}')
    ami_found = False
    for ami in resource['ec2_gendo_img_list']:
        print(f'Checking AMI: {ami["ImageId"]}')
        for tag in ami['Tags']:
            if tag['Key'] == 'Ec2ImageBuilderArn':
                print(f'Found Ec2ImageBuilderArn tag: {tag["Value"]}')
                match = re.search(r'gendo-recipe-(\d+)', tag['Value'])
                if match:
                    print(f'Extracted timestamp: {match.group(1)}, comparing with {timestamp}')
                    if match.group(1) == timestamp:
                        ami_found = True
                        print(f'Found AMI: {ami["ImageId"]} for version {timestamp}')
                        break
        if ami_found:
            break

    if not ami_found:
        print(f'AMI not found for version {timestamp}')
        return False

    # image recipe 리스트 확인
    print(f'Checking image recipe list for version {timestamp}')
    if not arn_list_any_imagebuilder_resource(resource['image_recipe_list'], timestamp):
        print(f'image recipe not found for version {timestamp}')
        return False

    # distribution 리스트 확인
    print(f'Checking distribution list for version {timestamp}')
    if not arn_list_any_imagebuilder_resource(resource['distribution_list'], timestamp):
        print(f'distribution not found for version {timestamp}')
        return False

    # pipeline 리스트 확인
    print(f'Checking pipeline list for version {timestamp}')
    if not arn_list_any_imagebuilder_resource(resource['pipe_line_list'], timestamp):
        print(f'pipeline not found for version {timestamp}')
        return False

    print(f'version {timestamp} exists in all resources')
    return True


def run_terminate_image(name):
    aws_cli = AWSCli()

    account_id = aws_cli.get_caller_account_id()
    imagebuilder_resource = dict()

    print_message('check in used ami version')
    ec2_describe_role_arn = ''
    for settings in env.get('imagebuilder', list()):
        if settings['NAME'] == 'run_terminate_imagebuilder_gendo_old_environment':
            ec2_describe_role_arn = settings['EC2_DESCRIBE_ROLE_ARN']

    if ec2_describe_role_arn:
        cmd = ['sts', 'assume-role']
        cmd += ['--role-arn', ec2_describe_role_arn]
        cmd += ['--role-session-name', 'ec2-describe-role']
        rr = aws_cli.run(cmd)

        access_key = rr['Credentials']['AccessKeyId']
        secret_key = rr['Credentials']['SecretAccessKey']
        session_token = rr['Credentials']['SessionToken']

        aws_cli_for_ec2 = AWSCli(aws_access_key=access_key,
                                 aws_secret_access_key=secret_key,
                                 aws_session_token=session_token)

        cmd = ['elasticbeanstalk', 'describe-environments']
        rr = aws_cli_for_ec2.run(cmd)

        gendo_eb_name_list = list()
        for r in rr['Environments']:
            if r['EnvironmentName'].startswith('gendo'):
                gendo_eb_name_list.append((r['EnvironmentName']))

        in_use_ec2_ami_list = list()
        for eb_name in gendo_eb_name_list:
            cmd = ['ec2', 'describe-instances']
            cmd += ['--filters', f'Name=tag:elasticbeanstalk:environment-name,Values={eb_name}']
            rr = aws_cli_for_ec2.run(cmd)
            if rr['Reservations'] and rr['Reservations'][0]['Instances']:
                in_use_ec2_ami_list.append(rr['Reservations'][0]['Instances'][0]['ImageId'])

    print_message(f'in_use_ec2_ami_list : {in_use_ec2_ami_list}')

    print_message('get All imagebuilder resouce version')

    print_message('describe log groups imagebuilder resouce')
    cmd = ['logs', 'describe-log-groups']
    cmd += ['--log-group-name-prefix', '/aws/imagebuilder/gendo']
    rr = aws_cli.run(cmd, ignore_error=True)
    imagebuilder_cw_log_list = rr['logGroups']

    cmd = ['ec2', 'describe-images']
    cmd += ['--filters=Name=name,Values="Gendo*"']
    cmd += ['--owners', account_id]
    rr = aws_cli.run(cmd)
    ec2_gendo_img_list = rr['Images']

    in_use_ami_timestamp_version = list()
    for img in ec2_gendo_img_list:
        if not img['ImageId'] in in_use_ec2_ami_list:
            continue
        for tag in img['Tags']:
            if tag['Key'] == 'Ec2ImageBuilderArn':
                m = re.search('/gendo-recipe-(.+?)/', tag['Value'])
                in_use_ami_timestamp_version.append(m.group(1))
    print_message(f'in_use_ami_timestamp_version : {in_use_ami_timestamp_version}')
    print_message(f'Currently in-use versions: {sorted(in_use_ami_timestamp_version)}')

    # Get all images with pagination
    ami_arn_list = []
    cmd = ['imagebuilder', 'list-images']
    rr = aws_cli.run(cmd)
    ami_arn_list.extend(filter_imagebuilder_resource_arn_list(rr['imageVersionList']))
    while 'nextToken' in rr:
        next_token = rr['nextToken']
        next_cmd = ['imagebuilder', 'list-images', '--next-token', next_token]
        next_rr = aws_cli.run(next_cmd)
        ami_arn_list.extend(filter_imagebuilder_resource_arn_list(next_rr['imageVersionList']))
        rr = next_rr

    # Get all pipelines with pagination
    pipe_line_list = []
    cmd = ['imagebuilder', 'list-image-pipelines']
    rr = aws_cli.run(cmd)
    pipe_line_list.extend(filter_imagebuilder_resource_arn_list(rr['imagePipelineList']))
    while 'nextToken' in rr:
        next_token = rr['nextToken']
        next_cmd = ['imagebuilder', 'list-image-pipelines', '--next-token', next_token]
        next_rr = aws_cli.run(next_cmd)
        pipe_line_list.extend(filter_imagebuilder_resource_arn_list(next_rr['imagePipelineList']))
        rr = next_rr

    # Get all distributions with pagination
    distribution_list = []
    cmd = ['imagebuilder', 'list-distribution-configurations']
    rr = aws_cli.run(cmd)
    distribution_list.extend(filter_imagebuilder_resource_arn_list(rr['distributionConfigurationSummaryList']))
    while 'nextToken' in rr:
        next_token = rr['nextToken']
        next_cmd = ['imagebuilder', 'list-distribution-configurations', '--next-token', next_token]
        next_rr = aws_cli.run(next_cmd)
        distribution_list.extend(filter_imagebuilder_resource_arn_list(next_rr['distributionConfigurationSummaryList']))
        rr = next_rr

    # Get all infrastructures with pagination
    infrastructure_list = []
    cmd = ['imagebuilder', 'list-infrastructure-configurations']
    rr = aws_cli.run(cmd)
    infrastructure_list.extend(filter_imagebuilder_resource_arn_list(rr['infrastructureConfigurationSummaryList']))
    while 'nextToken' in rr:
        next_token = rr['nextToken']
        next_cmd = ['imagebuilder', 'list-infrastructure-configurations', '--next-token', next_token]
        next_rr = aws_cli.run(next_cmd)
        infrastructure_list.extend(
            filter_imagebuilder_resource_arn_list(next_rr['infrastructureConfigurationSummaryList']))
        rr = next_rr

    # Get all image recipes with pagination
    image_recipe_list = []
    cmd = ['imagebuilder', 'list-image-recipes']
    rr = aws_cli.run(cmd)
    image_recipe_list.extend(filter_imagebuilder_resource_arn_list(rr['imageRecipeSummaryList']))
    while 'nextToken' in rr:
        next_token = rr['nextToken']
        next_cmd = ['imagebuilder', 'list-image-recipes', '--next-token', next_token]
        next_rr = aws_cli.run(next_cmd)
        image_recipe_list.extend(filter_imagebuilder_resource_arn_list(next_rr['imageRecipeSummaryList']))
        rr = next_rr

    print_message('get component list')
    # Get all components with pagination
    component_list = []
    cmd = ['imagebuilder', 'list-components']
    rr = aws_cli.run(cmd)
    component_list.extend(filter_imagebuilder_resource_arn_list(rr['componentVersionList']))
    while 'nextToken' in rr:
        next_token = rr['nextToken']
        next_cmd = ['imagebuilder', 'list-components', '--next-token', next_token]
        next_rr = aws_cli.run(next_cmd)
        component_list.extend(filter_imagebuilder_resource_arn_list(next_rr['componentVersionList']))
        rr = next_rr

    timestamp_list = list()
    for cc in component_list:
        # component ARN에서 타임스탬프 추출 (gendo-image-provisioning-00-component-1748308561)
        match = re.search(r'gendo-image-provisioning-\d+-component-(\d+)/', cc)

        if match:
            timestamp_list.append(match.group(1))
    timestamp_list = set(timestamp_list)

    imagebuilder_resource['imagebuilder_cw_log_list'] = imagebuilder_cw_log_list
    imagebuilder_resource['ami_arn_list'] = ami_arn_list
    imagebuilder_resource['ec2_gendo_img_list'] = ec2_gendo_img_list
    imagebuilder_resource['pipe_line_list'] = pipe_line_list
    imagebuilder_resource['distribution_list'] = distribution_list
    imagebuilder_resource['infrastructure_list'] = infrastructure_list
    imagebuilder_resource['image_recipe_list'] = image_recipe_list
    imagebuilder_resource['component_list'] = component_list
    imagebuilder_resource['in_use_ami_timestamp_version'] = in_use_ami_timestamp_version

    normal_resource_version_list = list()
    abnormal_resource_version_list = list()
    for tt in timestamp_list:
        rr = check_exist_resource_version(imagebuilder_resource, tt)
        if rr:
            normal_resource_version_list.append(tt)
        else:
            abnormal_resource_version_list.append(tt)

    print_message(f'normal resource version list : {normal_resource_version_list}')
    print_message(f'abnormal resource version list : {abnormal_resource_version_list}')

    delete_version_list = list(abnormal_resource_version_list)

    tt = datetime.now() - timedelta(weeks=8)
    timestamp_8_weeks_ago = time.mktime(tt.timetuple())
    print_message(f'8 weeks ago timestamp: {timestamp_8_weeks_ago}')

    all_timestamps = set()

    for cc in component_list:
        match = re.search(r'gendo-image-provisioning-\d+-component-(\d+)/', cc)
        if match:
            all_timestamps.add(match.group(1))

    for pp in pipe_line_list:
        match = re.search(r'gendo-pipeline-(\d+)$', pp)
        if match:
            all_timestamps.add(match.group(1))

    for dd in distribution_list:
        match = re.search(r'gendo-distribution-(\d+)$', dd)
        if match:
            all_timestamps.add(match.group(1))

    for ii in infrastructure_list:
        match = re.search(r'gendo-infrastructure-(\d+)$', ii)
        if match:
            all_timestamps.add(match.group(1))

    for rr in image_recipe_list:
        match = re.search(r'gendo-recipe-(\d+)/', rr)
        if match:
            all_timestamps.add(match.group(1))

    print_message(f'All timestamps from all resources: {sorted(all_timestamps)}')

    older_than_8_weeks_list = list()
    for timestamp in all_timestamps:
        if timestamp not in in_use_ami_timestamp_version and int(timestamp) < int(timestamp_8_weeks_ago):
            older_than_8_weeks_list.append(timestamp)

    print_message(f'Versions older than 8 weeks: {sorted(older_than_8_weeks_list)}')
    delete_version_list.extend(older_than_8_weeks_list)
    print_message(f'Final delete version list : {sorted(delete_version_list)}')

    print_message('delete cloudwatch image builder logs')
    for log_group in imagebuilder_cw_log_list:
        if delete_version_list_any_cloudwatch_log(delete_version_list, log_group):
            cmd = ['logs', 'delete-log-group']
            cmd += ['--log-group-name', log_group['logGroupName']]
            aws_cli.run(cmd, ignore_error=True)

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
            print(f'Delete pipeline: {pipe_line}')
            cmd = ['imagebuilder', 'delete-image-pipeline']
            cmd += ['--image-pipeline-arn', pipe_line]
            aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} distributions')
    for distribution in distribution_list:
        if delete_version_list_any_imagebuilder_resource(delete_version_list, distribution):
            print(f'Delete distribution: {distribution}')
            cmd = ['imagebuilder', 'delete-distribution-configuration']
            cmd += ['--distribution-configuration-arn', distribution]
            aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} infrastructures')
    for infrastructure in infrastructure_list:
        if delete_version_list_any_imagebuilder_resource(delete_version_list, infrastructure):
            print(f'Delete infrastructure: {infrastructure}')
            cmd = ['imagebuilder', 'delete-infrastructure-configuration']
            cmd += ['--infrastructure-configuration-arn', infrastructure]
            aws_cli.run(cmd)

    print_message(f'delete imagebuilder {name} image-recipes')
    for image_recipe in image_recipe_list:
        if delete_version_list_any_imagebuilder_resource(delete_version_list, image_recipe):
            print(f'Delete image recipe: {image_recipe}')
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
                    print(f'Delete component: {component}')
                    cmd = ['imagebuilder', 'delete-component']
                    cmd += ['--component-build-version-arn', r['arn']]
                    aws_cli.run(cmd, ignore_error=True)


################################################################################
#
# start
#
################################################################################
print_session('terminate imagebuilder gendo old environment')

name = 'gendo'
run_terminate_image(name)
