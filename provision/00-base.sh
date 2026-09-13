#!/bin/bash

set -euo pipefail
set -x

export DEBIAN_FRONTEND=noninteractive

cat >/etc/apt/apt.conf.d/90-golem-conffiles <<'EOF'
DPkg::Options { "--force-confold"; };
EOF
chmod 0644 /etc/apt/apt.conf.d/90-golem-conffiles

apt-get update
