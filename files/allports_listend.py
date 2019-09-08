#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daemon that runs allports shown."""
import json  # pylint: disable=unused-import
import html
import subprocess
import argparse
import logging
import sys
from flask import Flask, request
from systemd.journal import JournaldLogHandler

DEBUG = False
FAPP = Flask(__name__)

ABOUT = """
<!DOCTYPE html>
<html>
<head>
<title>openports.co - About</title>
<script async defer src="https://buttons.github.io/buttons.js"></script>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"></script>
<script>
  (adsbygoogle = window.adsbygoogle || []).push({{
    google_ad_client: "ca-pub-4487810698769604",
    enable_page_level_ads: true
  }});
</script>
</head>
<body>
<h2>public site: <a href="http://openports.co">openports.co</a></h2>

<a class="github-button" href="https://github.com/shollingsworth/terraform-module-allports-listening" data-icon="octicon-star" data-size="large" data-show-count="true" aria-label="Star shollingsworth/terraform-module-allports-listening on GitHub">Star</a>

<a class="github-button" href="https://github.com/shollingsworth" data-size="large" data-show-count="true" aria-label="Follow @shollingsworth on GitHub">Follow @shollingsworth</a>

<a class="github-button" href="https://github.com/shollingsworth/terraform-module-allports-listening/subscription" data-icon="octicon-eye" data-size="large" data-show-count="true" aria-label="Watch shollingsworth/terraform-module-allports-listening on GitHub">Watch</a>

<a class="github-button" href="https://github.com/shollingsworth/terraform-module-allports-listening/issues" data-icon="octicon-issue-opened" data-size="large" data-show-count="true" aria-label="Issue shollingsworth/terraform-module-allports-listening on GitHub">Issue</a>

<a class="github-button" href="https://github.com/shollingsworth/terraform-module-allports-listening/archive/master.zip" data-icon="octicon-cloud-download" data-size="large" aria-label="Download shollingsworth/terraform-module-allports-listening on GitHub">Download</a>

</body>
</html>
""".strip()

DOC = """
<!DOCTYPE html>
<html>
<head>
<title>Network Diagnostic - openports.co - Open Port:{dest_port}</title>
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"></script>
<script>
  (adsbygoogle = window.adsbygoogle || []).push({{
    google_ad_client: "ca-pub-4487810698769604",
    enable_page_level_ads: true
  }});
</script>
</head>
<body>
<h2>Open Port: <b>{dest_port}</b></h2>
<pre>
from : {client_ip}:{client_port}
agent: {agent}
<hr>
<b>This is a network diagnostic tool</b><br><br>
perform web requests, or use curl to verify if a port is open from internal to external.<br>
<b>example:</b><code> curl openports.co:8080 <code/>
<h3><a href="/about">More Information</a></h3>
</pre>
</body>
</html>
""".strip()

def _getprivip():
    cmd = [
        'ip',
        '-o',
        '-f',
        'inet',
        'addr',
        'show',
    ]
    output = subprocess.check_output(cmd).decode('utf-8').strip().split('\n')
    for _ in output:
        if ' lo ' in _:
            continue
        return _.split()[3].split('/')[0]

FORWARD_IF = 'eth0'
START_PORT = 10000
PRIV_IP = _getprivip()


@FAPP.route('/about')
def about():  # pylint: disable=unused-argument
    """Static about doc."""
    client_ip, _ = (
        request.remote_addr,
        request.environ.get('REMOTE_PORT'),
    )
    rline = request.full_path
    LOG.info(
        'About visit: %s / %s',
        client_ip,
        rline,
    )
    return ABOUT


@FAPP.route('/', defaults={'path': ''}, methods=['POST', 'GET'])
@FAPP.route('/<path:path>')
def catch_all(path):  # pylint: disable=unused-argument
    """Catches all paths."""
    client_ip, client_port = (
        request.remote_addr,
        request.environ.get('REMOTE_PORT'),
    )
    rline = request.full_path
    try:
        _ = request.headers['Host'].split(':')
    except AttributeError as i:
        LOG.exception('Unknown host: %s', i)
        return ''

    if len(_) == 1:
        dest_ip, dest_port = _, 80
    else:

        dest_ip, dest_port = _

    uid = (
        f'client:{client_ip}:{client_port}'
        f' -> srv_port:{dest_port}'
    )
    dest_ip, dest_port = (
        html.escape(str(dest_ip)),
        html.escape(str(dest_port)),
    )
    LOG.info(
        '%s / path: %s',
        uid,
        rline,
    )
    for i in request.headers.keys():
        LOG.info(
            '%s / header:%s: %s',
            uid,
            i,
            request.headers[i]
        )

    if request.data:
        LOG.info(
            '%s / data:%s',
            uid,
            request.data,
        )

    if request.form:
        LOG.info(
            '%s / form:%r',
            uid,
            request.form,
        )

    # respond
    return DOC.format(**{
        'client_ip': html.escape(client_ip),
        'client_port': html.escape(str(client_port)),
        'dest_port': dest_port,
        'agent': html.escape(request.headers['User-Agent']),
    }).encode()


def run_setup_commands():
    """Run iptables / networking setup comands."""
    # Split the ports up, exclude ssh, divide evenly otherwise
    sections = []
    new = []
    for i in range(0, 65535):
        match = i % 65535
        if match == 0 and new:
            sections.append(new)
            new = [i]
        elif i == 22:
            sections.append(new)
            new = []
        else:
            new.append(i)
    # This will always need to be appended
    new.append(65535)
    sections.append(new)
    port_blocks = [
        (min(i), max(i), len(i))
        for i in sections
    ]
    # Flush existing rules
    cmds = [
        [
            'sudo',
            'iptables',
            '-F',
        ],
        [
            'sudo',
            'iptables',
            '-F',
            '-t', 'nat',
        ],
    ]
    # For each block, increment listening port by one
    for start_port, end_port, _ in port_blocks:
        cmds.append([
            'sudo',
            'iptables',
            '-t', 'nat',
            '-A', 'PREROUTING',
            '-i', FORWARD_IF,
            '-p', 'tcp',
            '--dport', f'{start_port}:{end_port}',
            '-j', 'DNAT',
            '--to', f'{PRIV_IP}:{START_PORT}',
        ])
    for i in cmds:
        cmd = ' '.join(i)
        out = subprocess.check_output(i)
        print(f'running: {cmd} / {out}')

def main():
    """Run main function."""
    run_setup_commands()
    FAPP.run(host=PRIV_IP, port=START_PORT, debug=DEBUG)


if __name__ == '__main__':
    # logging.basicConfig()
    LOG = logging.getLogger('allports-listening')

    PARSER = argparse.ArgumentParser()
    PARSER.add_argument(
        '-l',
        '--logger',
        help='type of logger',
        choices=['stdout', 'systemd'],
        default='stdout',
        type=str,
    )
    ARGS = PARSER.parse_args()
    if ARGS.logger == 'systemd':
        HANDLER = JournaldLogHandler()
    else:
        HANDLER = logging.StreamHandler(sys.stdout)
    HANDLER.setFormatter(logging.Formatter(
        '[%(levelname)s] %(message)s'
    ))
    LOG.addHandler(HANDLER)
    LOG.setLevel(logging.INFO)
    logging.getLogger('werkzeug').setLevel(logging.WARN)
    main()
