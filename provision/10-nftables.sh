#!/bin/bash

set -euxo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get -y install --no-install-recommends nftables

install -d -m 0755 /etc/nftables.d

cat >/etc/nftables.conf <<'EOF'
#!/usr/sbin/nft -f

add table inet filter
flush table inet filter

include "/etc/nftables.d/*.conf"
EOF

cat >/etc/nftables.d/00-base.conf <<'EOF'
table inet filter {
    chain input {
        type filter hook input priority filter
        policy drop

        ct state established,related accept
        ct state invalid drop

        iif lo accept

        ip protocol icmp accept
        ip6 nexthdr ipv6-icmp accept

        tcp dport 22 accept
    }

    chain forward {
        type filter hook forward priority filter
        policy drop
    }

    chain output {
        type filter hook output priority filter
        policy accept
    }
}
EOF

chmod 0644 /etc/nftables.d/00-base.conf
systemctl enable nftables
