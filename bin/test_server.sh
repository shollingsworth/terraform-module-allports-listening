#!/bin/bash
ip="${1?"argv0: test_server_ip"}"
while true; do
    port="${RANDOM}"
    echo -ne '.'
    cmd="curl ${ip}:${port}"
    echo "${cmd}"
    # shellcheck disable=SC2086
    timeout 1 ${cmd}
    sleep 1
done
