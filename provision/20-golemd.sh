#!/bin/bash

set -euo pipefail
set -x

install -d -m 0700 /etc/golem
install -d -m 0700 /var/lib/golem

install -m 0755 /tmp/golemd /usr/local/bin/golemd
rm -f /tmp/golemd

cat >/etc/systemd/system/golemd.service <<'EOF'
[Unit]
Description=golem agent
After=network-online.target
Wants=network-online.target
ConditionPathExists=/etc/golem/token
ConditionPathExists=/etc/golem/secret-key

[Service]
ExecStart=/usr/local/bin/golemd \
    --host %H \
    --listen 127.0.0.1:7474 \
    --auth-token-file /etc/golem/token \
    --secrets-key-file /etc/golem/secret-key \
    --state-dir /var/lib/golem \
    --reconciler host
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl enable golemd.service
