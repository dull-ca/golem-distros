#!/bin/bash

set -euxo pipefail

cloud-init clean --logs --seed || true

printf 'uninitialized\n' >/etc/machine-id
chmod 0444 /etc/machine-id
