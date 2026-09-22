#!/bin/bash

set -euxo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get -y install --no-install-recommends ca-certificates curl

curl -fsSL https://repos.insights.digitalocean.com/sonar-agent.asc \
    -o /usr/share/keyrings/digitalocean-agent-keyring.asc
chmod 0644 /usr/share/keyrings/digitalocean-agent-keyring.asc

cat >/etc/apt/sources.list.d/digitalocean-agent.list <<'EOF'
deb [signed-by=/usr/share/keyrings/digitalocean-agent-keyring.asc] https://repos.insights.digitalocean.com/apt/do-agent main main
EOF
chmod 0644 /etc/apt/sources.list.d/digitalocean-agent.list

apt-get update
apt-get -y install --no-install-recommends do-agent
