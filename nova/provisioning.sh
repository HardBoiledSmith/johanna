#!/usr/bin/env bash
set -e

echo -e "##############################\nLINE NUMBER: "$LINENO"\n##############################"

PP=/opt/python/ondeck/app/configuration
PHASE=`cat ${PP}/phase`
EC2_INSTANCE_ID=`curl http://169.254.169.254/latest/meta-data/instance-id`
EC2_INSTANCE_ID=${EC2_INSTANCE_ID:2:6}
EC2_AVAILABILITY_ZONE=`curl http://169.254.169.254/latest/meta-data/placement/availability-zone`
HOSTNAME=${PHASE}"-nova-"${EC2_AVAILABILITY_ZONE}"-"${EC2_INSTANCE_ID}

sed -i -e "s@^HOSTNAME=.*@HOSTNAME="${HOSTNAME}"@" /etc/sysconfig/network
echo "127.0.0.1   ${HOSTNAME}" >> /etc/hosts
hostname ${HOSTNAME}
service network restart

echo -e "##############################\nLINE NUMBER: "$LINENO"\n##############################"

touch /etc/server_info
EC2_INSTANCE_ID=`curl http://169.254.169.254/latest/meta-data/instance-id`
EC2_AVAILABILITY_ZONE=`curl http://169.254.169.254/latest/meta-data/placement/availability-zone`
echo "AWS_EC2_INSTANCE_ID=${EC2_INSTANCE_ID}" >> /etc/server_info
echo "AWS_EC2_AVAILABILITY_ZONE=${EC2_AVAILABILITY_ZONE}" >> /etc/server_info

echo -e "##############################\nLINE NUMBER: "$LINENO"\n##############################"

mkdir -p /etc/nova

echo -e "##############################\nLINE NUMBER: "$LINENO"\n##############################"

PP=/opt/python/ondeck/app/configuration
cp    ${PP}/etc/nova/settings_local.py    /etc/nova/settings_local.py

echo -e "##############################\nLINE NUMBER: "$LINENO"\n##############################"

cd /opt/python/ondeck/app/nova
./manage.py collectstatic --noinput
mv /opt/nova/static ..

echo -e "##############################\nLINE NUMBER: "$LINENO"\n##############################"

chown -R wsgi: /opt/python/ondeck/app/static
