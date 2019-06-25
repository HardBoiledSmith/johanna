import json

from run_common import AWSCli
from run_common import print_message
from run_common import print_session


def run_create_s3_bucket(name, settings):
    aws_cli = AWSCli()

    acl = settings['ACL']
    bucket_name = settings['BUCKET_NAME']
    expire_days = settings.get('EXPIRE_FILES_DAYS', 0)
    is_web_hosting = settings["WEB_HOSTING"]
    region = settings['REGION']

    ################################################################################
    print_session('create %s' % name)

    ################################################################################

    cmd = ['s3api', 'create-bucket', '--bucket', bucket_name, '--create-bucket-configuration',
           'LocationConstraint=%s' % region]
    cmd += ['--acl', acl]
    aws_cli.run(cmd)

    ################################################################################
    print_message('set web hosting')

    ################################################################################

    if is_web_hosting:
        cc = {
            "IndexDocument": {
                "Suffix": "index.html"
            },
            "ErrorDocument": {
                "Key": "error.html"
            }
        }
        cmd = ['s3api', 'put-bucket-website', '--bucket', bucket_name]
        cmd += ['--website-configuration', json.dumps(cc)]
        aws_cli.run(cmd)

    ################################################################################
    print_message('set policy')

    ################################################################################

    pp = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::%s/*" % bucket_name
            }
        ]
    }
    cmd = ['s3api', 'put-bucket-policy', '--bucket', bucket_name]
    cmd += ['--policy', json.dumps(pp)]
    aws_cli.run(cmd)

    ################################################################################
    print_message('set life cycle')

    ################################################################################

    if expire_days > 0:
        cc = {
            "Rules": [
                {
                    "Expiration": {
                        "Days": expire_days,
                        "ExpiredObjectDeleteMarker": False
                    },
                    "ID": "clean-up-after-%d-days" % expire_days,
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
