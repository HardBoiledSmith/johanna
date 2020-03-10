import json

from run_common import AWSCli


def create_replication_bucket(aws_access_key, aws_secretkey, origin_bucket_account_id, replication_bucket_name):
    # 복제 대상 iam 키값으로 실행
    aws_cli = AWSCli()  # 변경 필요 awsCli() 부분은 access key, secretkey로 변경할 수 있도록.

    cmd = ['s3api', 'create-bucket', '--bucket', replication_bucket_name, '--create-bucket-configuration',
           'LocationConstraint=%s' % 'ap-northeast-2']
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['s3api', 'delete-public-access-block']
    cmd += ['--bucket', replication_bucket_name]
    aws_cli.run(cmd)

    cmd = ['s3api', 'put-bucket-versioning']
    cmd += ['--bucket', replication_bucket_name]
    cmd += ['--versioning-configuration', 'Status=Enabled']
    aws_cli.run(cmd)

    s3_policy = {
        "Version": "2008-10-17",
        "Statement": [
            {
                "Sid": "1",
                "Effect": "Allow",
                "Principal": {
                    "AWS": "arn:aws:iam::%s:root" % origin_bucket_account_id
                },
                "Action": [
                    "s3:ReplicateObject",
                    "s3:ReplicateDelete"
                ],
                "Resource": [
                    "arn:aws:s3:::%s" % replication_bucket_name,
                    "arn:aws:s3:::%s/*" % replication_bucket_name
                ]
            }
        ]
    }

    cmd = ['s3api', 'put-bucket-policy',
           '--bucket', replication_bucket_name,
           '--policy', json.dumps(s3_policy)]
    aws_cli.run(cmd)


def run_create_s3_srr_bucket():
    aws_cli = AWSCli()

    origin_bucket_name = ''  # please input origin bucket name
    replication_bucket_name = ''  # please input replication bucket name
    origin_bucket_account_id = ''  # please input origin bucket account id

    cmd = ['s3api', 'create-bucket', '--bucket', origin_bucket_name, '--create-bucket-configuration',
           'LocationConstraint=%s' % 'ap-northeast-2']
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['s3api', 'delete-public-access-block']
    cmd += ['--bucket', origin_bucket_name]
    aws_cli.run(cmd)

    cmd = ['s3api', 'put-bucket-versioning']
    cmd += ['--bucket', origin_bucket_name]
    cmd += ['--versioning-configuration', 'Status=Enabled']
    aws_cli.run(cmd)

    create_replication_bucket('', '', origin_bucket_account_id, replication_bucket_name)

    # ### 원본 iam 키값으로 실행
    s3_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": [
                    "s3:Get*",
                    "s3:ListBucket"
                ],
                "Effect": "Allow",
                "Resource": [
                    "arn:aws:s3:::%s" % origin_bucket_name,
                    "arn:aws:s3:::%s/*" % origin_bucket_name
                ]
            },
            {
                "Action": [
                    "s3:ReplicateObject",
                    "s3:ReplicateDelete",
                    "s3:ReplicateTags",
                    "s3:GetObjectVersionTagging"
                ],
                "Effect": "Allow",
                "Resource": "arn:aws:s3:::%s/*" % replication_bucket_name
            }
        ]
    }

    srr_policy_name = ''  # please input you want policy name
    srr_role_name = ''  # please input you want role name
    cmd = ['iam', 'create-policy']
    cmd += ['--policy-name', srr_policy_name]
    cmd += ['--policy-document', json.dumps(s3_policy)]
    aws_cli.run(cmd, ignore_error=True)

    cc = ['iam', 'create-role']
    cc += ['--role-name', srr_role_name]
    cc += ['--path', '/']
    cc += ['--assume-role-policy-document', 'file://aws_iam/aws-s3-bucket-role.json']
    aws_cli.run(cc)

    cc = ['iam', 'attach-role-policy']
    cc += ['--role-name', srr_role_name]
    cc += ['--policy-arn', 'arn:aws:iam::%s:policy/%s' % (origin_bucket_account_id, srr_policy_name)]
    aws_cli.run(cc)

    s3_policy = {
        "Role": "arn:aws:iam::%s:role/%s" % (origin_bucket_account_id, srr_role_name),
        "Rules": [
            {
                "Status": "Enabled",
                "Priority": 1,
                "DeleteMarkerReplication": {"Status": "Disabled"},
                "Filter": {"Prefix": ""},
                "Destination": {
                    "Bucket": "arn:aws:s3:::%s" % replication_bucket_name
                }
            }
        ]
    }

    cc = ['s3api', 'put-bucket-replication']
    cc += ['--bucket', origin_bucket_name]
    cc += ['--replication-configuration', json.dumps(s3_policy)]
    aws_cli.run(cc)


run_create_s3_srr_bucket()
