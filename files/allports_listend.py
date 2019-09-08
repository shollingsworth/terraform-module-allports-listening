#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daemon that runs allports shown."""
import json  # pylint: disable=unused-import
import http.server
import html
import socketserver
import threading
import subprocess
import argparse
import logging
import sys
from systemd.journal import JournaldLogHandler

LOG = logging.getLogger('allports-listening')
JD_HANDLER = JournaldLogHandler()
JD_HANDLER.setFormatter(logging.Formatter(
    '[%(levelname)s] %(message)s'
))
STDOUT_HANDLER = logging.StreamHandler(sys.stdout)
LOG.addHandler(JD_HANDLER)
LOG.addHandler(STDOUT_HANDLER)
LOG.setLevel(logging.INFO)


DOC = """
<!DOCTYPE html>
<html>
<body>
<p>Open Port: <b>{dest_port}</b></p>
<pre>
from : {client_ip}:{client_port}
agent: {agent}
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


def get_server_config(listener_number):
    """Get arguments for each server thread."""
    for i in range(int(listener_number)):
        yield PRIV_IP, START_PORT + i


def run_setup_commands(listener_number):
    """Run iptables / networking setup comands."""

    div = int(65535 / int(listener_number))
    # Split the ports up, exclude ssh, divide evenly otherwise
    sections = []
    new = []
    for i in range(0, 65535):
        match = i % div
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
    for idx, (start_port, end_port, _) in enumerate(port_blocks):
        dest_port = START_PORT + idx
        cmds.append([
            'sudo',
            'iptables',
            '-t', 'nat',
            '-A', 'PREROUTING',
            '-i', FORWARD_IF,
            '-p', 'tcp',
            '--dport', f'{start_port}:{end_port}',
            '-j', 'DNAT',
            '--to', f'{PRIV_IP}:{dest_port}',
        ])
    for i in cmds:
        cmd = ' '.join(i)
        out = subprocess.check_output(i)
        print(f'running: {cmd} / {out}')



class PortsResponse(http.server.BaseHTTPRequestHandler):
    """Customer request handler for ports request."""
    def _log_data(self, data=None):
        """Log Data from POST/GET request."""
        client_ip, client_port = self.client_address
        rline = self.requestline
        try:
            _ = self.headers['Host'].split(':')
        except AttributeError as i:
            LOG.exception('Unknown host: %s', i)
            raise

        if len(_) == 1:
            dest_ip, dest_port = _, 80
        else:
            dest_ip, dest_port = _

        uid = f'client:{client_ip}:{client_port} -> srv_port:{dest_port}'
        dest_ip, dest_port = html.escape(str(dest_ip)), html.escape(str(dest_port))
        LOG.info(
            '%s / %s',
            uid,
            rline,
        )
        for i in self.headers.keys():
            LOG.info('%s / header:%s: %s', uid, i, self.headers[i])

        if data:
            LOG.info('%s / payload: %s', uid, data)

        # respond
        self.wfile.write(DOC.format(**{
            'client_ip': html.escape(client_ip),
            'client_port': html.escape(str(client_port)),
            'dest_port': dest_port,
            'agent': html.escape(self.headers['User-Agent']),
        }).encode())


    def do_POST(self):   # pylint: disable=invalid-name
        """Process post request."""
        content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
        post_data = self.rfile.read(content_length) # <--- Gets the data itself
        self.send_response(200)
        self.end_headers()
        self._log_data(post_data)


    def do_GET(self):   # pylint: disable=invalid-name
        """handle get request."""
        self.send_response(200)
        self.end_headers()
        self._log_data()


def server(address, port):
    """Simple http server."""
    handler = PortsResponse
    with socketserver.TCPServer((address, port), handler) as httpd:
        print("serving at port", port)
        httpd.serve_forever()


def main(args):
    """Run main function."""
    run_setup_commands(args.thread_count)
    threads = []
    for i in get_server_config(args.thread_count):
        thr = threading.Thread(target=server, args=(i))
        threads.append(thr)
    for i in threads:
        i.start()
    for i in threads:
        i.join()


if __name__ == '__main__':
    PARSER = argparse.ArgumentParser()
    PARSER.add_argument(
        'thread_count',
        help='Number of servers to spawn',
        type=str,
    )
    ARGS = PARSER.parse_args()
    main(ARGS)
