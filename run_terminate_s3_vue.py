import json

from run_common import AWSCli
from run_common import print_message


def run_terminate_s3_vue(name, settings):
    aws_cli = AWSCli()

    deploy_bucket_name = settings['BUCKET_NAME']

    ################################################################################
    print_message('terminate %s' % name)

    ################################################################################
    print_message('cleanup deploy bucket')

    cmd = ['s3', 'rm', 's3://%s' % deploy_bucket_name, '--recursive']
    delete_result = aws_cli.run(cmd, ignore_error=True)
    for ll in delete_result.split('\n'):
        print(ll)

    ################################################################################
    print_message('remove tag from deploy bucket')

    cmd = ['s3api', 'delete-bucket-tagging', '--bucket', deploy_bucket_name]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete web hosting')

    cmd = ['s3api', 'delete-bucket-website', '--bucket', deploy_bucket_name]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete policy')

    cmd = ['s3api', 'delete-bucket-policy', '--bucket', deploy_bucket_name]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('restore public access block')

    pp = {
        "BlockPublicAcls": True,
        "IgnorePublicAcls": True,
        "BlockPublicPolicy": True,
        "RestrictPublicBuckets": True
    }
    cmd = ['s3api', 'put-public-access-block', '--bucket', deploy_bucket_name]
    cmd += ['--public-access-block-configuration', json.dumps(pp)]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('invalidate cache from cloudfront')

    cf_dist_id = settings.get('CLOUDFRONT_DIST_ID', '')
    if len(cf_dist_id) > 0:
        cmd = ['cloudfront', 'create-invalidation', '--distribution-id', cf_dist_id, '--paths', '/*']
        invalidate_result = aws_cli.run(cmd, ignore_error=True)
        print(invalidate_result)
