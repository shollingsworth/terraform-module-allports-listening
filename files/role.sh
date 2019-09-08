#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

echo ALLPORTS-LISTENING > /etc/hostname
hostname -F /etc/hostname


/usr/sbin/useradd -r \
	-d /var/lib/allports \
	-s /sbin/nologin \
	-c "allports daemon" \
	allports


mkdir  -p /var/lib/allports
chown allports:allports /var/lib/allports

cat <<EOF > /etc/sysctl.conf
net.ipv4.conf.all.route_localnet = 1
net.ipv4.conf.all.forwarding = 1
net.ipv4.ip_forward = 1
EOF
sysctl -p /etc/sysctl.conf


echo '%allports ALL=(ALL) NOPASSWD: /usr/sbin/iptables' > /etc/sudoers.d/allports

cat <<EOF > /usr/lib/systemd/system/allports.service
[Unit]
Description=Start Allports Listener Service
After=network.target

[Service]
ExecStart=/usr/local/sbin/allports_listend.py -l systemd
User=allports
Group=allports
Type=simple
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable allports.service
systemctl start allports.service
