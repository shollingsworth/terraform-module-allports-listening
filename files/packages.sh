#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

apt -y update
apt -y full-upgrade

apt -y install python3-pip libsystemd-dev
pip3 install systemd flask
