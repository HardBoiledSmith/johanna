#!/usr/bin/env python3
import subprocess

from env import env
import os
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import read_file
import json
import time

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def run_create_image_builder():
    aws_cli = AWSCli()

    phase = env['common']['PHASE']
    git_url = "git@github.com:HardBoiledSmith/gendo.git"
    name = 'gendo'
    template_path = 'template/%s' % name
    git_rev = ['git', 'rev-parse', 'HEAD']
    git_hash_johanna = subprocess.Popen(git_rev, stdout=subprocess.PIPE).communicate()[0]

    ##############################################################################
    print_message('git clone')

    subprocess.Popen(['rm', '-rf', template_path]).communicate()
    subprocess.Popen(['mkdir', '-p', template_path]).communicate()

    if phase == 'dv':
        git_command = ['git', 'clone', '--depth=1', git_url]
    else:
        git_command = ['git', 'clone', '--depth=1', '-b', phase, git_url]
    subprocess.Popen(git_command, cwd=template_path).communicate()
    if not os.path.exists('%s/%s' % (template_path, name)):
        raise Exception()

    git_hash_app = subprocess.Popen(git_rev,
                                    stdout=subprocess.PIPE,
                                    cwd='%s/%s' % (template_path, name)).communicate()[0]

    subprocess.Popen(['rm', '-rf', './%s/.git' % name], cwd=template_path).communicate()
    subprocess.Popen(['rm', '-rf', './%s/.gitignore' % name], cwd=template_path).communicate()

    ############################################################################
    semantic_version = '0.0.0'
    str_timestamp = str(int(time.time()))

    print_session('create component')

    gendo_component_name = f'gendo_provisioning_component_{str_timestamp}'

    file_path_name = 'template/gendo/gendo/requirements.txt'
    tmp_lines = read_file(file_path_name)
    lines = list()

    for ll in tmp_lines:
        ll = ll.replace('\n', '')
        tt = f'{" "*14}pip install {ll}\n'
        lines.append(tt)
    pp = ''.join(lines)

    sample_filename_path = 'template/gendo/gendo/_provisioning/gendo_golden_image_sample.yml'
    filename_path = 'template/gendo/gendo/_provisioning/gendo_golden_image.yml'
    with open(filename_path, 'w') as ff:
        with open(sample_filename_path, 'r') as f:
            tmp_list = f.readlines()
            for line in tmp_list:
                if 'requirements.txt' in line:
                    ff.write(pp)
                else:
                    ff.write(line)

    tag0 = 'git_hash_johanna=%s' % git_hash_johanna.decode('utf-8').strip()
    tag1 = 'git_hash_%s=%s' % (name, git_hash_app.decode('utf-8').strip())

    cmd = ['imagebuilder', 'create-component']
    cmd += ['--name', gendo_component_name]
    cmd += ['--semantic-version', semantic_version]
    cmd += ['--platform', 'Windows']
    # TODO: env로 전환 supported-os-versions
    cmd += ['--supported-os-versions', 'Microsoft Windows Server 2016']
    cmd += ['--tags', f'{tag0},{tag1}']
    cmd += ['--data', 'file://template/gendo/gendo/_provisioning/gendo_golden_image.yml']

    rr = aws_cli.run(cmd)
    gendo_component_arn = rr['componentBuildVersionArn']

    ############################################################################
    print_session('create recipe')

    recipe_components = list()

    recipe_component = dict()
    recipe_component['componentArn'] = gendo_component_arn
    recipe_components.append(recipe_component)

    cmd = ['imagebuilder', 'list-components']
    cmd += ['--owner', 'Amazon']
    cmd += ['--filters', 'name=name,values="aws-cli-version-2-windows"']
    rr = aws_cli.run(cmd)
    recipe_component = dict()
    arn = rr['componentVersionList'][-1]['arn']
    recipe_component['componentArn'] = arn
    recipe_components.append(recipe_component)

    cmd = ['ec2', 'describe-images']
    cmd += ['--owner', 'amazon']
    cmd += ['--filters',
            'Name=name,Values=aws-elasticbeanstalk-amzn-??????????.x86_64-WindowsServer2016-V2-hvm-*',
            'Name=state,Values=available']
    cmd += ['--query', 'reverse(sort_by(Images, &CreationDate))[:1].ImageId']
    cmd += ['--output', 'text']
    cmd += ['--region', 'ap-northeast-2']
    latest_eb_platform_ami = aws_cli.run(cmd)

    cmd = ['elasticbeanstalk', 'describe-platform-version']
    cmd += ['--region', 'ap-northeast-2']
    cmd += ['--platform-arn',
            'arn:aws:elasticbeanstalk:ap-northeast-2::platform/IIS 10.0 running on 64bit Windows Server 2016/2.6.8']
    cmd += ['--query', 'PlatformDescription.CustomAmiList']
    rr = aws_cli.run(cmd)

    eb_platform_ami = ''
    for vv in rr:
        if vv['VirtualizationType'] == 'hvm':
            eb_platform_ami = vv['ImageId']

    if latest_eb_platform_ami != eb_platform_ami:
        update_required = True

    recipe_name = f'gendo_recipe_{str_timestamp}'
    cmd = ['imagebuilder', 'create-image-recipe']
    cmd += ['--name', recipe_name]
    cmd += ['--working-directory', '/tmp']
    cmd += ['--semantic-version', semantic_version]
    cmd += ['--components', json.dumps(recipe_components)]
    cmd += ['--parent-image', eb_platform_ami]
    rr = aws_cli.run(cmd)
    gendo_recipe_arn = rr['imageRecipeArn']

    ############################################################################
    print_session('create infrastructure')

    infrastructure_name = f'gendo_infrastructure_{str_timestamp}'
    cmd = ['imagebuilder', 'create-infrastructure-configuration']
    cmd += ['--name', infrastructure_name]
    cmd += ['--instance-profile-name', 'EC2InstanceProfileForImageBuilder']
    cmd += ['--instance-types', 'r5.large']
    cmd += ['--terminate-instance-on-failure']
    # cmd += ['--sns-topic-arn', topic_arn]
    rr = aws_cli.run(cmd)
    gendo_infrastructure_arn = rr['infrastructureConfigurationArn']

    ############################################################################
    print_session('create distribution')

    distributions = [
        {
            "region": "ap-northeast-2",
            "amiDistributionConfiguration": {
                "name": "Gendo_{{ imagebuilder:buildDate }}",
                "launchPermission": {
                }
            }
        }
    ]

    distribution_name = f'gendo_distribution_{str_timestamp}'
    cmd = ['imagebuilder', 'create-distribution-configuration']
    cmd += ['--name', distribution_name]
    cmd += ['--distributions', json.dumps(distributions)]
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
    rr = aws_cli.run(cmd)

    gendo_pipeline_arn = rr['imagePipelineArn']

    ###########################################################################
    print_session('excution pipeline for image')
    cmd = ['imagebuilder', 'start-image-pipeline-execution']
    cmd += ['--image-pipeline-arn', gendo_pipeline_arn]
    aws_cli.run(cmd)

    if update_required:
        print_session('Pleas Check Your eb platfrom version // '
                      'Reference : https://docs.aws.amazon.com/elasticbeanstalk/latest/platforms/'
                      'platforms-supported.html#platforms-supported.net')

################################################################################
#
# start
#
################################################################################


print_session('create image builder')

run_create_image_builder()
