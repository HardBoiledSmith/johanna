import json

from run_common import AWSCli
from run_common import print_message
from run_common import print_session


def run_terminate_s3_bucket(name, settings):
    aws_cli = AWSCli()

    bucket_name = settings['BUCKET_NAME']

    ################################################################################
    print_session('terminate %s' % name)

    ################################################################################
    print_message('delete life cycle')

    cmd = ['s3api', 'delete-bucket-lifecycle', '--bucket', bucket_name]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete web hosting')

    cmd = ['s3api', 'delete-bucket-website', '--bucket', bucket_name]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete policy')

    cmd = ['s3api', 'delete-bucket-policy', '--bucket', bucket_name]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete cors')

    cmd = ['s3api', 'delete-bucket-cors', '--bucket', bucket_name]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('restore public access block')

    pp = {
        "BlockPublicAcls": True,
        "IgnorePublicAcls": True,
        "BlockPublicPolicy": True,
        "RestrictPublicBuckets": True
    }
    cmd = ['s3api', 'put-public-access-block', '--bucket', bucket_name]
    cmd += ['--public-access-block-configuration', json.dumps(pp)]
    aws_cli.run(cmd, ignore_error=True)
