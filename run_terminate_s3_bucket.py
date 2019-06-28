from run_common import AWSCli
from run_common import print_message
from run_common import print_session


def run_terminate_s3_bucket(name, settings):
    aws_cli = AWSCli()

    bucket_name = settings['BUCKET_NAME']
    expire_days = settings.get('EXPIRE_FILES_DAYS', 0)
    is_web_hosting = settings["WEB_HOSTING"]

    ################################################################################
    print_session('terminate %s' % name)

    ################################################################################
    print_message('delete public access block')

    cmd = ['s3api', 'delete-public-access-block', '--bucket', bucket_name]
    aws_cli.run(cmd)

    ################################################################################
    print_message('delete web hosting')

    if is_web_hosting:
        cmd = ['s3api', 'delete-bucket-website', '--bucket', bucket_name]
        aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete policy')

    cmd = ['s3api', 'delete-bucket-policy', '--bucket', bucket_name]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################
    print_message('delete life cycle')

    if expire_days > 0:
        cmd = ['s3api', 'delete-bucket-lifecycle', '--bucket', bucket_name]
        aws_cli.run(cmd, ignore_error=True)
