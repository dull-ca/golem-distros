#!/bin/bash

set -euo pipefail
set -x

cat >/etc/cloud/cloud.cfg.d/91-datasource.cfg <<'EOF'
datasource_list: [ ConfigDrive, None ]
EOF

chmod 0644 /etc/cloud/cloud.cfg.d/91-datasource.cfg
