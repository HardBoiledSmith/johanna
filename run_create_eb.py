#!/usr/bin/env python3

from env import env
from run_common import AWSCli
from run_common import check_template_availability
from run_common import print_session
from run_create_eb_cron_job import run_create_eb_cron_job
from run_create_eb_django import run_create_eb_django
from run_create_eb_graphite_grafana import run_create_eb_graphite_grafana
from run_create_eb_openvpn import run_create_eb_openvpn

args = []

if __name__ == "__main__":
    from run_common import parse_args

    args = parse_args()


def _get_s3_bucket_name(settings):
    aws_cli = AWSCli()

    result = aws_cli.run(['s3', 'ls'])

    bucket_name = None
    # noinspection PyTypeChecker
    for rr in result.split('\n'):
        print(rr)
        # noinspection PyTypeChecker
        bucket_name = rr.split(' ')[2]
        # noinspection PyTypeChecker,PyUnresolvedReferences
        if bucket_name.startswith('elasticbeanstalk-%s-' % settings['AWS_DEFAULT_REGION']):
            break
        bucket_name = None

    if not bucket_name:
        raise Exception('cannot find any elasticbeanstalk bucket in AWS Seoul region.')

    # noinspection PyTypeChecker
    bucket_name = 's3://' + bucket_name
    print(bucket_name)

    return bucket_name


################################################################################
#
# start
#
################################################################################
print_session('create eb')

################################################################################
check_template_availability()

eb = env['elasticbeanstalk']
if len(args) == 2:
    target_eb_name = args[1]
    target_eb_name_exists = False
    for eb_env in eb['ENVIRONMENTS']:
        if eb_env['NAME'] == target_eb_name:
            target_eb_name_exists = True
            if eb_env['TYPE'] == 'cron job':
                run_create_eb_cron_job(eb_env['NAME'], eb_env)
                continue
            if eb_env['TYPE'] == 'django':
                run_create_eb_django(eb_env['NAME'], eb_env)
                continue
            if eb_env['TYPE'] == 'openvpn':
                run_create_eb_openvpn(eb_env['NAME'], eb_env)
                continue
            if eb_env['TYPE'] == 'graphite/grafana':
                run_create_eb_graphite_grafana(eb_env['NAME'], eb_env)
                continue
            print('"%s" is not supported' % eb_env['TYPE'])
            raise Exception()
    if not target_eb_name_exists:
        print('"%s" is not exists in config.json' % target_eb_name)
else:
    for eb_env in eb['ENVIRONMENTS']:
        if eb_env['TYPE'] == 'cron job':
            run_create_eb_cron_job(eb_env['NAME'], eb_env)
            continue
        if eb_env['TYPE'] == 'django':
            run_create_eb_django(eb_env['NAME'], eb_env)
            continue
        if eb_env['TYPE'] == 'openvpn':
            run_create_eb_openvpn(eb_env['NAME'], eb_env)
            continue
        if eb_env['TYPE'] == 'graphite/grafana':
            run_create_eb_graphite_grafana(eb_env['NAME'], eb_env)
            continue
        print('"%s" is not supported' % eb_env['TYPE'])
        raise Exception()
