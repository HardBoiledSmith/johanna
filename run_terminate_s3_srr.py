from run_common import AWSCli
from run_common import print_message


def run_terminate_s3_replication():
    aws_cli = AWSCli()  # 파라메터 방법에 대해 설명 요청 후 해당 세팅으로 변경.

    replication_bucket_name = ''  # please input replication bucket name

    cmd = ['s3api', 'put-bucket-versioning']
    cmd += ['--bucket', replication_bucket_name]
    cmd += ['--versioning-configuration', 'Status=Suspended']
    aws_cli.run(cmd, ignore_error=False)

    cmd = ['s3api', 'list-object-versions']
    cmd += ['--bucket', replication_bucket_name]
    rr = aws_cli.run(cmd, ignore_error=False)

    delete_list = dict()
    for r in rr['Versions']:
        delete_list[r['Key']] = r['VersionId']

    for ll in delete_list:
        cmd = ['s3api', 'delete-object']
        cmd += ['--bucket', replication_bucket_name]
        cmd += ['--key', ll]
        cmd += ['--version-id', delete_list[ll]]
        aws_cli.run(cmd, ignore_error=False)

    cmd = ['s3api', 'delete-bucket']
    cmd += ['--bucket', replication_bucket_name]
    aws_cli.run(cmd, ignore_error=False)


def run_terminate_s3_origin_srr():
    aws_cli = AWSCli()

    ################################################################################
    print_message('origin buket delete policy')

    srr_policy_name = ''  # please input you want policy name
    srr_role_name = ''  # please input you want role name
    origin_bucket_name = ''  # please input origin bucket name
    origin_bucket_account_id = ''  # please input origin bucket account id

    cmd = ['iam', 'detach-role-policy']
    cmd += ['--role-name', srr_role_name]
    cmd += ['--policy-arn', 'arn:aws:iam::%s:policy/%s' % (origin_bucket_account_id, srr_policy_name)]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'delete-policy']
    cmd += ['--policy-arn', 'arn:aws:iam::%s:policy/%s' % (origin_bucket_account_id, srr_policy_name)]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['iam', 'delete-role']
    cmd += ['--role-name', srr_role_name]
    aws_cli.run(cmd, ignore_error=True)

    cmd = ['s3api', 'delete-bucket-replication']
    cmd += ['--bucket', origin_bucket_name]
    aws_cli.run(cmd, ignore_error=False)

    cmd = ['s3api', 'put-bucket-versioning']
    cmd += ['--bucket', origin_bucket_name]
    cmd += ['--versioning-configuration', 'Status=Suspended']
    aws_cli.run(cmd, ignore_error=False)

    cmd = ['s3api', 'list-object-versions']
    cmd += ['--bucket', origin_bucket_name]
    rr = aws_cli.run(cmd, ignore_error=False)

    delete_list = dict()
    for r in rr['Versions']:
        delete_list[r['Key']] = r['VersionId']

    for ll in delete_list:
        cmd = ['s3api', 'delete-object']
        cmd += ['--bucket', origin_bucket_name]
        cmd += ['--key', ll]
        cmd += ['--version-id', delete_list[ll]]
        aws_cli.run(cmd, ignore_error=False)

    cmd = ['s3api', 'delete-bucket']
    cmd += ['--bucket', origin_bucket_name]
    aws_cli.run(cmd, ignore_error=False)


run_terminate_s3_origin_srr()
run_terminate_s3_replication()
