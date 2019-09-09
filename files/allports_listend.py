
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

# Double escape json
CLI_DOC = """
{{
    "client_ip":"{client_ip}",
    "port": "{dest_port}",
    "port_name": "{port_name}",
    "port_desc": "{port_desc}",
    "agent": "{agent}",
    "status": "OPEN"
}}
""".lstrip()

DOC = """
<!DOCTYPE html>
<html>
<head>
<title>Network Diagnostic - openports.co - Open Port:{dest_port}</title>
</head>
<body>
<h2>
    {previous_url_x}
    {previous_url}
    Open Port:
    <b>{dest_port}</b>
    {next_url}
    {next_url_x}
</h2>
<pre>
port info : {port_name} / {port_desc}
from      : {client_ip}:{client_port}
agent     : {agent}
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

def _getport_dict():
    data = [
        i.split()
        for i in open('/etc/services', 'r').read().split('\n')
        if not i.startswith('#')
        and i
    ]

    port_dict = {}
    for i in data:
        name, port, *_ = i
        desc = ' '.join(_)
        port_num, proto = port.split('/')
        desc = desc.lstrip('#').strip()
        port_dict[f'{proto}/{port_num}'] = [name, desc]
    return port_dict

FORWARD_IF = 'eth0'
NGINX_PORT = 9999
FLASK_PORT = 10000
PRIV_IP = _getprivip()
PORT_DICT = _getport_dict()


@FAPP.route('/about')
def about():  # pylint: disable=unused-argument
    """Static about doc."""
    client_ip, _ = (
        request.headers['X-Real-Ip'],
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
def catch_all(path):  # pylint: disable=unused-argument,too-many-locals
    """Catches all paths."""
    client_ip, client_port = (
        request.headers['X-Real-Ip'],
        request.headers['X-Real-PORT'],
    )

    rline = request.full_path


    # Grab remote connection info
    _ = request.headers['X-SRV-HOST'].split(':')
    if len(_) == 1:
        _ = (_[0], 80)
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

    try:
        uagent = request.headers['User-Agent']
    except KeyError as _:
        LOG.error('Unknown Agent: %s', _)
        uagent = 'UNKNOWN'

    uagent = html.escape(uagent)

    previous_port = int(dest_port) - 1
    previous_port_x = int(dest_port) - 10

    previous_url = '' if int(dest_port) == 1 else 'http://{0}:{1}'.format(
        dest_ip,
        previous_port,
    )

    previous_url_x = '' if (int(dest_port) - 10) <= 1 else 'http://{0}:{1}'.format(
        dest_ip,
        previous_port_x,
    )

    next_port = int(dest_port) + 1
    next_port_x = int(dest_port) + 10

    next_url_x = '' if (int(dest_port) + 10) >= 65535 else 'http://{0}:{1}'.format(
        dest_ip,
        next_port_x,
    )

    next_url = '' if int(dest_port) >= 65535 else 'http://{0}:{1}'.format(
        dest_ip,
        next_port,
    )

    next_url_x = '<a href="{0}">&nbsp;&nbsp;&gt;&gt;</a>'.format(next_url_x) \
        if next_url_x else ''

    previous_url_x = '<a href="{0}">&nbsp;&nbsp;&lt;&lt;</a>'.format(previous_url_x) \
        if previous_url_x else ''

    next_url = '<a href="{0}">&gt;</a>'.format(next_url) if next_url else ''
    previous_url = '<a href="{0}">&lt;</a>'.format(previous_url) if previous_url else ''

    match_cli = any([
        'curl' in uagent.lower(),
        'python' in uagent.lower(),
        'wget' in uagent.lower(),
        'unknown' in uagent.lower(),
    ])

    CLIENT_RESPONSE = CLI_DOC if match_cli else DOC  # pylint: disable=invalid-name
    port_name, port_desc = PORT_DICT.get(f'tcp/{dest_port}', ['unknown', 'unknown'])
    port_desc = '-' if not port_desc else port_desc

    # respond
    return CLIENT_RESPONSE.format(**{
        'port_name': port_name,
        'port_desc': port_desc,
        'previous_url_x': previous_url_x,
        'next_url_x': next_url_x,
        'previous_url': previous_url,
        'next_url': next_url,
        'client_ip': html.escape(client_ip),
        'client_port': html.escape(str(client_port)),
        'dest_port': dest_port,
        'agent': uagent,
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
            '--to', f'{PRIV_IP}:{NGINX_PORT}',
        ])
    for i in cmds:
        cmd = ' '.join(i)
        out = subprocess.check_output(i)
        print(f'running: {cmd} / {out}')

def main():
    """Run main function."""
    run_setup_commands()
    FAPP.run(host='127.0.0.1', port=FLASK_PORT, debug=DEBUG)


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
