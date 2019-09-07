#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

apt -y update
apt -y full-upgrade
