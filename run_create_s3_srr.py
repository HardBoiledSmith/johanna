import json
import time

from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import read_file, re_sub_lines


def run_create_s3_bucket(name, settings):
    aws_cli = AWSCli()

    bucket_name = settings['BUCKET_NAME']
    expire_days = settings.get('EXPIRE_FILES_DAYS', 0)
    is_web_hosting = settings['WEB_HOSTING']
    region = settings['REGION']
    policy = settings.get('POLICY', '')

    ################################################################################
    print_session('create %s' % name)

    cmd = ['s3api', 'create-bucket', '--bucket', bucket_name, '--create-bucket-configuration',
           'LocationConstraint=%s' % region]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################

    if policy in ['website', 'email']:
        print_message('delete public access block')

        cmd = ['s3api', 'delete-public-access-block']
        cmd += ['--bucket', bucket_name]
        aws_cli.run(cmd)

        cmd = ['s3api', 'put-bucket-versioning']
        cmd += ['--bucket', bucket_name]
        cmd += ['--versioning-configuration', 'Status=Enabled']
        aws_cli.run(cmd)

        print_message('wait public access block has deleted...')
        time.sleep(10)

        print_message('set bucket policy')

        lines = read_file('aws_iam/aws-s3-bucket-policy-for-%s.json' % policy)
        lines = re_sub_lines(lines, 'BUCKET_NAME', bucket_name)
        pp = ' '.join(lines)

        cmd = ['s3api', 'put-bucket-policy']
        cmd += ['--bucket', bucket_name]
        cmd += ['--policy', pp]
        aws_cli.run(cmd)

    if is_web_hosting:
        print_message('set website configuration')

        cmd = ['s3api', 'put-bucket-website']
        cmd += ['--bucket', bucket_name]
        cmd += ['--website-configuration',
                'file://aws_iam/aws-s3-website-configuration.json']
        aws_cli.run(cmd)

    ################################################################################
    if expire_days > 0:
        print_message('set life cycle rule')

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


### 원본의 iam 키값으로 실행
aws_cli = AWSCli()
cmd = ['s3api', 'create-bucket', '--bucket', 'dv-srr-test', '--create-bucket-configuration',
       'LocationConstraint=%s' % 'ap-northeast-2']
aws_cli.run(cmd, ignore_error=True)

cmd = ['s3api', 'delete-public-access-block']
cmd += ['--bucket', 'dv-srr-test']
aws_cli.run(cmd)

cmd = ['s3api', 'put-bucket-versioning']
cmd += ['--bucket', 'dv-srr-test']
cmd += ['--versioning-configuration', 'Status=Enabled']
aws_cli.run(cmd)

### 복제 대상 iam 키값으로 실행
cmd = ['s3api', 'create-bucket', '--bucket', 'qa-srr-test', '--create-bucket-configuration',
       'LocationConstraint=%s' % 'ap-northeast-2']
aws_cli.run(cmd, ignore_error=True)

cmd = ['s3api', 'delete-public-access-block']
cmd += ['--bucket', 'qa-srr-test']
aws_cli.run(cmd)

cmd = ['s3api', 'put-bucket-versioning']
cmd += ['--bucket', 'qa-srr-test']
cmd += ['--versioning-configuration', 'Status=Enabled']
aws_cli.run(cmd)

cmd = ['s3api', 'put-bucket-policy',
       '--bucket', 'qa-srr-test',
       '--policy', 'file://aws_iam/aws-s3-bucket-policy-for-replication.json']
aws_cli.run(cmd)


### 원본 iam 키값으로 실
cmd = ['iam', 'create-policy']
cmd += ['--policy-name', 'srr-test-policy']
cmd += ['--policy-document', 'file://aws_iam/aws-s3-bucket-policy-for-srr.json']
aws_cli.run(cmd, ignore_error=True)

cc = ['iam', 'create-role']
cc += ['--role-name', 'srr-test']
cc += ['--path', '/']
cc += ['--assume-role-policy-document', 'file://aws_iam/aws-s3-bucket-role.json']
aws_cli.run(cc)

cc = ['iam', 'attach-role-policy']
cc += ['--role-name', 'srr-test']
cc += ['--policy-arn', 'arn:aws:iam::020858000170:policy/srr-test-policy']
aws_cli.run(cc)

cc = ['s3api', 'put-bucket-replication']
cc += ['--bucket', 'dv-srr-test']
cc += ['--replication-configuration', 'file://aws_iam/aws-s3-bucket-policy-for-replication-srr.json']
aws_cli.run(cc)




