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

systemctl enable nginx.service

# doesn't always come up on boot listening on the right port
cat <<EOF > /etc/nginx/nginx.conf
user www-data;
worker_processes auto;
pid /run/nginx.pid;
# include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 768;
}

http {
    server {
        listen 9999;
        listen [::]:9999;

        server_name openports.co;

        location / {
            proxy_pass http://127.0.0.1:10000/;
            proxy_set_header X-Real-IP \$remote_addr;
            proxy_set_header X-Real-PORT \$remote_port;
            proxy_set_header X-SRV-HOST \$http_host;
        }
    }
}
EOF

sleep 5
systemctl start nginx.service
systemctl restart nginx.service
