#!/usr/bin/env bash
set -e

echo -e "##############################\nLINE NUMBER: "$LINENO"\n##############################"

cp /vagrant/id_rsa ~/.ssh/

echo -e "##############################\nLINE NUMBER: "$LINENO"\n##############################"

cp /etc/apt/sources.list /etc/apt/sources.list.backup
sed -i -e '/^deb/s#http://.*archive.ubuntu.com/ubuntu#http://kr.archive.ubuntu.com/ubuntu#' -e '/^deb/s#http://.*security.ubuntu.com/ubuntu#http://kr.archive.ubuntu.com/ubuntu#' /etc/apt/sources.list

apt-get -y clean
apt-get -y update

echo -e "##############################\nLINE NUMBER: "$LINENO"\n##############################"

export DEBIAN_FRONTEND=noninteractive

apt-get -y install gdebi-core
apt-get -y install git
apt-get -y install python-pip

echo -e "##############################\nLINE NUMBER: "$LINENO"\n##############################"

cd /opt

for i in `seq 1 10`;
do
	echo 'Git clone try count: '${i}

	# Non interactive git clone (ssh fingerprint prompt)
	ssh-keyscan github.com > ~/.ssh/known_hosts || true
	git clone git@github.com:addnull/johanna.git || true
	if [ -d /opt/johanna ]; then
		break
	fi

	sleep 3
done

echo -e "##############################\nLINE NUMBER: "$LINENO"\n##############################"

cd /opt/johanna

pip install -r requirements.txt
cp env.py.sample env.py
