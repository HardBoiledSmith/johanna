#!/usr/bin/env python3
import json
import os
import subprocess
import time
from datetime import datetime
from shutil import copyfile

from pytz import timezone

from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import read_file
from run_create_imagebuilder_iam import create_iam_profile_for_imagebuilder

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def run_create_image_builder(options):
    aws_cli = AWSCli()

    phase = 'dv'
    git_url = "git@github.com:HardBoiledSmith/gendo.git"
    name = 'gendo'
    template_path = 'template/%s' % name
    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]

    ##############################################################################
    print_message('git clone')

    subprocess.Popen(['rm', '-rf', template_path]).communicate()
    subprocess.Popen(['mkdir', '-p', template_path]).communicate()

    branch = options.get('branch', 'master' if phase == 'dv' else phase)
    print(f'branch: {branch}')
    git_command = ['git', 'clone', '--depth=1', '-b', branch, git_url]
    subprocess.Popen(git_command, cwd=template_path).communicate()
    print(f'{template_path}/{name}')
    if not os.path.exists(f'{template_path}/{name}'):
        raise Exception()

    git_hash_app = subprocess.Popen(git_rev,
                                    stdout=subprocess.PIPE,
                                    cwd='%s/%s' % (template_path, name)).communicate()[0]

    subprocess.Popen(['rm', '-rf', './%s/.git' % name], cwd=template_path).communicate()
    subprocess.Popen(['rm', '-rf', './%s/.gitignore' % name], cwd=template_path).communicate()
    ############################################################################
    print_session('create role')

    instance_profile_name, role_arn = create_iam_profile_for_imagebuilder(name)

    ############################################################################

    print_session('elastic beanstalk ami latest version check')

    target_eb_platform_version = aws_cli.get_eb_gendo_windows_platform(target_service='imagebuilder')

    cmd = ['ec2', 'describe-images']
    cmd += ['--owner', 'amazon']
    cmd += ['--filters',
            'Name=name,Values=aws-elasticbeanstalk-amzn-??????????.x86_64-WindowsServer2022-V2-hvm-*',
            'Name=state,Values=available']
    cmd += ['--query', 'reverse(sort_by(Images, &CreationDate))[:1].ImageId']
    cmd += ['--output', 'text']
    cmd += ['--region', 'ap-northeast-2']
    latest_eb_platform_ami = aws_cli.run(cmd)

    semantic_version = '0.0.0'
    str_timestamp = str(int(time.time()))
    cmd = ['elasticbeanstalk', 'describe-platform-version']
    cmd += ['--region', 'ap-northeast-2']
    cmd += ['--platform-arn',
            f'arn:aws:elasticbeanstalk:ap-northeast-2::platform/{target_eb_platform_version}']
    cmd += ['--query', 'PlatformDescription.CustomAmiList']

    try:
        rr = aws_cli.run(cmd)
    except Exception as ee:
        if latest_eb_platform_ami.strip() != target_eb_platform_version.strip():
            print_session('Pleas Check Your eb platfrom version. \n'
                          '----------------------------------------------------\n'
                          f'latest eb platform ami : {latest_eb_platform_ami}\n'
                          f'target eb platform ami : {target_eb_platform_version}\n '
                          '----------------------------------------------------\n'
                          'Reference : https://docs.aws.amazon.com/elasticbeanstalk/latest/platforms/'
                          'platforms-supported.html#platforms-supported.net')
        raise ee

    eb_platform_ami = ''
    for vv in rr:
        if vv['VirtualizationType'] == 'hvm':
            eb_platform_ami = vv['ImageId']

    print_session('create component')

    file_path_name = 'template/gendo/gendo/requirements.txt'
    tmp_lines = read_file(file_path_name)
    lines = list()

    for ll in tmp_lines:
        ll = ll.replace('\n', '')
        tt = f'{" " * 14}& pip install {ll}\n'
        lines.append(tt)
    pp = ''.join(lines)

    copyfile('template/gendo/gendo/_provisioning/gendo_image_provisioning_part1_sample.yml',
             'template/gendo/gendo/_provisioning/gendo_image_provisioning_part1.yml')

    sample_filename_path = 'template/gendo/gendo/_provisioning/gendo_image_provisioning_part2_sample.yml'
    filename_path = 'template/gendo/gendo/_provisioning/gendo_image_provisioning_part2.yml'
    with open(filename_path, 'w') as ff:
        with open(sample_filename_path, 'r') as f:
            tmp_list = f.readlines()
            for line in tmp_list:
                if 'REQUIREMENTS.TXT' in line:
                    ff.write(pp)
                else:
                    ff.write(line)

    git_hash_johanna_tag = f"git_hash_johanna={git_hash_johanna.decode('utf-8').strip()}"
    git_hash_gendo_tag = f"git_hash_{name}={git_hash_app.decode('utf-8').strip()}"
    target_eb_platform_version_tag = f'eb_platform={target_eb_platform_version}'

    gendo_component_name = f'gendo_provisioning_part1_component_{str_timestamp}'
    cmd = ['imagebuilder', 'create-component']
    cmd += ['--name', gendo_component_name]
    cmd += ['--semantic-version', semantic_version]
    cmd += ['--platform', 'Windows']
    cmd += ['--supported-os-versions', 'Microsoft Windows Server 2022']
    cmd += ['--tags', f'{git_hash_johanna_tag},{git_hash_gendo_tag},{target_eb_platform_version_tag}']
    cmd += ['--data', 'file://template/gendo/gendo/_provisioning/gendo_image_provisioning_part1.yml']

    rr = aws_cli.run(cmd)
    gendo_component_arn1 = rr['componentBuildVersionArn']

    gendo_component_name = f'gendo_provisioning_part2_component_{str_timestamp}'
    cmd = ['imagebuilder', 'create-component']
    cmd += ['--name', gendo_component_name]
    cmd += ['--semantic-version', semantic_version]
    cmd += ['--platform', 'Windows']
    cmd += ['--supported-os-versions', 'Microsoft Windows Server 2022']
    cmd += ['--tags', f'{git_hash_johanna_tag},{git_hash_gendo_tag},{target_eb_platform_version_tag}']
    cmd += ['--data', 'file://template/gendo/gendo/_provisioning/gendo_image_provisioning_part2.yml']

    rr = aws_cli.run(cmd)
    gendo_component_arn2 = rr['componentBuildVersionArn']

    gendo_component_name = f'gendo_provisioning_test_component_{str_timestamp}'
    cmd = ['imagebuilder', 'create-component']
    cmd += ['--name', gendo_component_name]
    cmd += ['--semantic-version', semantic_version]
    cmd += ['--platform', 'Windows']
    cmd += ['--supported-os-versions', 'Microsoft Windows Server 2022']
    cmd += ['--tags', f'{git_hash_johanna_tag},{git_hash_gendo_tag},{target_eb_platform_version_tag}']
    cmd += ['--data', 'file://template/gendo/gendo/_provisioning/gendo_image_provisioning_test_sample.yml']

    rr = aws_cli.run(cmd)
    gendo_test_component_arn = rr['componentBuildVersionArn']

    ############################################################################
    print_session('create recipe')

    recipe_components = list()

    recipe_component = dict()
    recipe_component['componentArn'] = gendo_component_arn1
    recipe_components.append(recipe_component)

    recipe_component = dict()
    recipe_component['componentArn'] = gendo_component_arn2
    recipe_components.append(recipe_component)

    recipe_component = dict()
    recipe_component['componentArn'] = gendo_test_component_arn
    recipe_components.append(recipe_component)

    base_ami_tag = f'base_ami_id={eb_platform_ami}'

    recipe_name = f'gendo_recipe_{str_timestamp}'
    cmd = ['imagebuilder', 'create-image-recipe']
    cmd += ['--name', recipe_name]
    cmd += ['--working-directory', '/tmp']
    cmd += ['--semantic-version', semantic_version]
    cmd += ['--components', json.dumps(recipe_components)]
    cmd += ['--parent-image', eb_platform_ami]
    cmd += ['--tags', f'{git_hash_johanna_tag},{git_hash_gendo_tag},{target_eb_platform_version_tag}, {base_ami_tag}']
    rr = aws_cli.run(cmd)
    gendo_recipe_arn = rr['imageRecipeArn']

    ############################################################################
    print_session('create infrastructure')

    utc_now = datetime.now(timezone('UTC'))
    kst_now = utc_now.astimezone(timezone('Asia/Seoul'))
    kst_date_time_now = kst_now.strftime("%Y년 %m월 %d일 %H:%M")

    infrastructure_name = f'gendo_infrastructure_{str_timestamp}'
    cmd = ['imagebuilder', 'create-infrastructure-configuration']
    cmd += ['--name', infrastructure_name]
    cmd += ['--instance-profile-name', instance_profile_name]
    cmd += ['--instance-types', 'r5.large']
    cmd += ['--terminate-instance-on-failure']
    cmd += ['--description', f'생성일자 : {kst_date_time_now}']
    cmd += ['--tags', f'{git_hash_johanna_tag},{git_hash_gendo_tag},{target_eb_platform_version_tag}, {base_ami_tag}']
    rr = aws_cli.run(cmd)
    gendo_infrastructure_arn = rr['infrastructureConfigurationArn']

    ############################################################################
    print_session('create distribution')

    distributions = [
        {
            "region": "ap-northeast-2",
            "amiDistributionConfiguration": {
                "name": "Gendo_{{ imagebuilder:buildDate }}",
                "amiTags": {f"git_hash_{name}": git_hash_app.decode('utf-8').strip()},
                "launchPermission": {
                    "organizationalUnitArns": [
                        'arn:aws:organizations::591379657681:ou/o-xmsbstr6zx/ou-37un-ad54n1d2',
                        'arn:aws:organizations::591379657681:ou/o-xmsbstr6zx/ou-37un-tylw4vwu'
                    ]
                }
            }
        }
    ]

    distribution_name = f'gendo_distribution_{str_timestamp}'
    cmd = ['imagebuilder', 'create-distribution-configuration']
    cmd += ['--name', distribution_name]
    cmd += ['--distributions', json.dumps(distributions)]
    cmd += ['--description', f'생성일자 : {kst_date_time_now}']
    cmd += ['--tags', f'{git_hash_johanna_tag},{git_hash_gendo_tag},{target_eb_platform_version_tag}, {base_ami_tag}']
    rr = aws_cli.run(cmd)
    gendo_distributions_arn = rr['distributionConfigurationArn']

    ###########################################################################
    print_session('create pipeline')

    pipeline_name = f'gendo_pipeline_{str_timestamp}'
    cmd = ['imagebuilder', 'create-image-pipeline']
    cmd += ['--name', pipeline_name]
    cmd += ['--image-recipe-arn', gendo_recipe_arn]
    cmd += ['--infrastructure-configuration-arn', gendo_infrastructure_arn]
    cmd += ['--distribution-configuration-arn', gendo_distributions_arn]
    cmd += ['--tags', f'{git_hash_johanna_tag},{git_hash_gendo_tag},{target_eb_platform_version_tag}, {base_ami_tag}']

    rr = aws_cli.run(cmd)

    gendo_pipeline_arn = rr['imagePipelineArn']

    ###########################################################################
    print_session('excution pipeline for image')
    cmd = ['imagebuilder', 'start-image-pipeline-execution']
    cmd += ['--image-pipeline-arn', gendo_pipeline_arn]
    aws_cli.run(cmd)


################################################################################
#
# start
#
################################################################################

print_session('create image builder')

run_create_image_builder(options)
