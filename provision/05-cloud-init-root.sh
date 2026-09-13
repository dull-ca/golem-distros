#!/bin/bash

set -euo pipefail
set -x

cat >/etc/cloud/cloud.cfg.d/90-golem.cfg <<'EOF'
disable_root: false
ssh_pwauth: false
system_info:
  default_user:
    name: root
    lock_passwd: true
    shell: /bin/bash
EOF
chmod 0644 /etc/cloud/cloud.cfg.d/90-golem.cfg

cat >/etc/ssh/sshd_config.d/10-golem.conf <<'EOF'
PermitRootLogin prohibit-password
PasswordAuthentication no
KbdInteractiveAuthentication no
EOF
chmod 0644 /etc/ssh/sshd_config.d/10-golem.conf
