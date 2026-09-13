#!/bin/bash

set -euo pipefail
set -x

export DEBIAN_FRONTEND=noninteractive

apt-get -y install --no-install-recommends kexec-tools
