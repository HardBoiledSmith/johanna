import json
import time

from env import env
from run_common import AWSCli
from run_common import print_message
from run_common import print_session
from run_common import read_file, re_sub_lines


def run_create_s3_bucket(name, settings):
    aws_cli = AWSCli()

    bucket_name = settings['BUCKET_NAME']
    expire_days = settings.get('EXPIRE_FILES_DAYS', 0)
    versioning_expire_days = settings.get('EXPIRE_VERSION_DAYS', 0)
    is_web_hosting = settings['WEB_HOSTING']
    region = settings['REGION']
    policy = settings.get('POLICY', '')
    phase = env['common']['PHASE']

    ################################################################################
    print_session('create %s' % name)

    cmd = ['s3api', 'create-bucket', '--bucket', bucket_name, '--create-bucket-configuration',
           'LocationConstraint=%s' % region]
    aws_cli.run(cmd, ignore_error=True)

    ################################################################################

    if policy in ['website', 'email', 'temp-bucket']:
        print_message('delete public access block')

        cmd = ['s3api', 'delete-public-access-block']
        cmd += ['--bucket', bucket_name]
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

    if policy == 'temp-bucket':
        print_message('set bucket policy')

        lines = read_file('aws_iam/aws-s3-bucket-policy-for-%s.json' % policy)
        lines = re_sub_lines(lines, 'BUCKET_NAME', bucket_name)
        lines = re_sub_lines(lines, 'BUCKET_NAME', bucket_name)
        pp = ' '.join(lines)

        cmd = ['s3api', 'put-bucket-policy']
        cmd += ['--bucket', bucket_name]
        cmd += ['--policy', pp]
        aws_cli.run(cmd)

        allowd_origins = list()
        if phase == 'op':
            allowd_origins.append('https://app.hbsmith.io')
            allowd_origins.append('https://app2.hbsmith.io')
        elif phase == 'qa':
            allowd_origins.append(f'https://{phase}-app.hbsmith.io')
            allowd_origins.append(f'https://{phase}-app.hbsmith.io')
        else:
            ii = bucket_name.find('-dv-hbsmith-temp')
            dev_name = bucket_name[0:ii]

            allowd_origins.append(f'https://{dev_name}-dv-app.hbsmith.io')
            allowd_origins.append(f'https://{dev_name}-dv-app.hbsmith.io')

        if not allowd_origins:
            raise Exception('Invalid allowed origin')

        print_message('set cors')
        cc = {
            "CORSRules": [
                {
                    "AllowedHeaders": ["*"],
                    "AllowedMethods": ["PUT"],
                    "AllowedOrigins": allowd_origins,
                    "ExposeHeaders": []
                }
            ]
        }

        cmd = ['s3api', 'put-bucket-cors']
        cmd += ['--bucket', bucket_name]
        cmd += ['--cors-configuration', json.dumps(cc)]
        aws_cli.run(cmd)

    if is_web_hosting:
        print_message('set website configuration')

        cmd = ['s3api', 'put-bucket-website']
        cmd += ['--bucket', bucket_name]
        cmd += ['--website-configuration',
                'file://aws_iam/aws-s3-website-configuration.json']
        aws_cli.run(cmd)

        print_message('set cors')
        cc = {
            "CORSRules": [
                {
                    "AllowedOrigins": ["*"],
                    "AllowedMethods": ["GET"],
                    "MaxAgeSeconds": 3000,
                    "AllowedHeaders": ["Authorization"]
                }
            ]
        }

        cmd = ['s3api', 'put-bucket-cors']
        cmd += ['--bucket', bucket_name]
        cmd += ['--cors-configuration', json.dumps(cc)]
        aws_cli.run(cmd)

    ################################################################################
    if 'hbsmith-script' in bucket_name:
        cmd = ['s3api', 'get-bucket-versioning']
        cmd += ['--bucket', bucket_name]
        rr = aws_cli.run(cmd)

        if rr and rr['Status'] == 'Enabled' and versioning_expire_days > 0:
            print_message('set script bucket life cycle rule')
            cc = {
                "Rules": [
                    {
                        "ID": "script_file_manage_rule",
                        "Status": "Enabled",
                        "Filter": {
                        },
                        "Expiration": {
                            "ExpiredObjectDeleteMarker": True
                        },
                        "NoncurrentVersionExpiration": {
                            "NoncurrentDays": versioning_expire_days
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
                        "NoncurrentDays": 7
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
