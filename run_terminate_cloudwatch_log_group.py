#!/usr/bin/env python3
import re
import time
from collections import defaultdict

from run_common import AWSCli
from run_common import print_message
from run_common import print_session

options, args = dict(), list()

if __name__ == "__main__":
    from run_common import parse_args

    options, args = parse_args()


def get_eb_log_groups():
    aws_cli = AWSCli()
    cmd = ['logs', 'describe-log-groups']
    cmd += ['--log-group-name-prefix', '/aws/elasticbeanstalk/']
    rr = aws_cli.run(cmd)
    return rr['logGroups']


def get_active_environments():
    aws_cli = AWSCli()
    cmd = ['elasticbeanstalk', 'describe-environments']
    cmd += ['--no-include-deleted']
    rr = aws_cli.run(cmd)

    active_envs = set()
    for _env in rr['Environments']:
        match = re.search(r'([^.]+)-(\d+)', _env['EnvironmentName'])
        if match:
            active_envs.add(_env['EnvironmentName'])

    return active_envs


def group_logs_by_app_and_timestamp(log_groups):
    app_logs = defaultdict(lambda: defaultdict(list))

    for log_group in log_groups:
        log_name = log_group['logGroupName']
        match = re.match(r'/aws/elasticbeanstalk/(.+)-(\d+)', log_name)
        if match:
            app_name = match.group(1)
            timestamp = match.group(2)
            app_logs[app_name][timestamp].append({
                'name': log_name,
                'creation': log_group['creationTime'],
                'arn': log_group.get('arn', ''),
                'env_id': f"{app_name}-{timestamp}"
            })

    return app_logs


def cleanup_old_logs(app_logs, active_envs, keep_count=1):
    aws_cli = AWSCli()
    deleted_count = 0

    for app_name, timestamp_groups in app_logs.items():
        print_message(f'Processing logs for application: {app_name}')

        sorted_timestamps = sorted(timestamp_groups.keys(), key=int, reverse=True)
        sorted_groups = [(timestamp, timestamp_groups[timestamp]) for timestamp in sorted_timestamps]

        if not sorted_groups:
            print('No log groups to delete')
            continue

        print(f'Found {len(sorted_groups)} apps')

        inactive_groups = []
        for timestamp, logs in sorted_groups:
            env_id = f"{app_name}-{timestamp}"
            if env_id not in active_envs:
                inactive_groups.append((timestamp, logs))

        if not inactive_groups:
            print('No inactive apps found')
            continue

        print(f'Found {len(inactive_groups)} inactive apps')

        groups_to_delete = inactive_groups[keep_count:]

        print(f'Delete {len(groups_to_delete)} apps in inactive apps (skipping keep last {keep_count})')

        for timestamp, logs in groups_to_delete:
            env_id = f"{app_name}-{timestamp}"
            print(f'Deleting log groups in apps for {env_id}')
            for log in logs:
                cmd = ['logs', 'delete-log-group']
                cmd += ['--log-group-name', log['name']]
                aws_cli.run(cmd, ignore_error=True)
                deleted_count += 1

    return deleted_count


################################################################################
#
# start
#
################################################################################
print_session('terminate old elasticbeanstalk log groups')

timestamp = int(time.time())

################################################################################
print_message('terminate old elasticbeanstalk log groups (current timestamp: %d)' % timestamp)

print_message('getting elasticbeanstalk log groups')
log_groups = get_eb_log_groups()

if not log_groups:
    print_message('no elasticbeanstalk log groups found')
else:
    print_message('getting active elasticbeanstalk environments')
    active_envs = get_active_environments()

    print_message('grouping logs by application and timestamp')
    app_logs = group_logs_by_app_and_timestamp(log_groups)

    print_message('starting cleanup process')
    deleted_count = cleanup_old_logs(app_logs, active_envs)

    print_message(f'cleanup complete. deleted {deleted_count} log groups')
