import json

from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import read_file, re_sub_lines


def run_create_s3_bucket(name, settings):
    aws_cli = AWSCli()

    bucket_name = settings['BUCKET_NAME']
    expire_days = settings.get('EXPIRE_FILES_DAYS', 0)
    is_web_hosting = settings["WEB_HOSTING"]
    region = settings['REGION']
    is_public_access_block = settings['PUBLIC_ACCESS_BLOCK']

    ################################################################################
    print_session('create %s' % name)

    ################################################################################

    cmd = ['s3api', 'create-bucket', '--bucket', bucket_name, '--create-bucket-configuration',
           'LocationConstraint=%s' % region]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('set website configuration')

    if is_web_hosting:
        cmd = ['s3api', 'put-bucket-website']
        cmd += ['--bucket', bucket_name]
        cmd += ['--website-configuration',
                'file://aws_s3/aws-s3-website-configuration-sample.json']
        aws_cli.run(cmd)
    else:
        cmd = ['s3api', 'delete-bucket-website', '--bucket', bucket_name]
        aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('set policy')

    pp = {
        "BlockPublicAcls": False,
        "IgnorePublicAcls": False,
        "BlockPublicPolicy": False,
        "RestrictPublicBuckets": False
    }
    cmd = ['s3api', 'put-public-access-block', '--bucket', bucket_name]
    cmd += ['--public-access-block-configuration', json.dumps(pp)]
    aws_cli.run(cmd)


    cmd = ['s3api', 'get-bucket-acl', '--bucket', bucket_name]
    aws_cli.run(cmd, ignore_error=True)

    lines = read_file('aws_s3/aws-s3-bucket-policy-sample.json')
    lines = re_sub_lines(lines, 'BUCKET_NAME', bucket_name)
    pp = ' '.join(lines)

    cmd = ['s3api', 'put-bucket-policy', '--bucket', bucket_name]
    cmd += ['--policy', pp]
    aws_cli.run(cmd)

    ################################################################################
    print_message('set public access block')

    pp = {
        "BlockPublicAcls": is_public_access_block,
        "IgnorePublicAcls": is_public_access_block,
        "BlockPublicPolicy": is_public_access_block,
        "RestrictPublicBuckets": is_public_access_block
    }
    cmd = ['s3api', 'put-public-access-block', '--bucket', bucket_name]
    cmd += ['--public-access-block-configuration', json.dumps(pp)]
    aws_cli.run(cmd)

    ################################################################################
    print_message('set life cycle')

    pp = {
        "BlockPublicAcls": False,
        "IgnorePublicAcls": False,
        "BlockPublicPolicy": False,
        "RestrictPublicBuckets": False
    }
    cmd = ['s3api', 'put-public-access-block', '--bucket', bucket_name]
    cmd += ['--public-access-block-configuration', json.dumps(pp)]
    aws_cli.run(cmd)



    ################################################################################
    print_message('set life cycle')

    if expire_days > 0:
        cc = {
            "Rules": [
                {
                    "Expiration": {
                        "Days": expire_days
                    },
                    "ID": "result_file_manage_rule",
                    "Filter": {
                        "Prefix": ""
                    },
                    "Status": "Enabled",
                    "NoncurrentVersionExpiration": {
                        "NoncurrentDays": expire_days
                    },
                    "AbortIncompleteMultipartUpload": {
                        "DaysAfterInitiation": 7
                    }
                }
            ]
        }

        cmd = ['s3api', 'put-bucket-lifecycle-configuration', '--bucket', bucket_name]
        cmd += ['--lifecycle-configuration', json.dumps(cc)]
        aws_cli.run(cmd)
    else:
        cmd = ['s3api', 'delete-bucket-lifecycle', '--bucket', bucket_name]
        aws_cli.run(cmd, ignore_error=True)
