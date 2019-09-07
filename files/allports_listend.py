#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daemon that runs allports shown."""
import json  # pylint: disable=unused-import
import http.server
import socketserver
import threading
import subprocess
import argparse

DOC = """
<!DOCTYPE html>
<html>
<body>
<p>Open Port: <b>{dest_port}</b></p>
<pre>
from : {client_ip}:{client_port}
to   : {dest_ip}:{dest_port}
agent: {agent}
</pre>
</body>
</html>
""".strip()

FORWARD_IF = 'eth0'
LISTEN_IP = '127.0.0.1'
START_PORT = 10000


def get_server_config(listener_number):
    """Get arguments for each server thread."""
    for i in range(int(listener_number)):
        yield LISTEN_IP, START_PORT + i


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
            '--to', f'{LISTEN_IP}:{dest_port}',
        ])
    for i in cmds:
        cmd = ' '.join(i)
        out = subprocess.check_output(i)
        print(f'running: {cmd} / {out}')



class PortsResponse(http.server.BaseHTTPRequestHandler):
    """Customer request handler for ports request."""
    def do_GET(self):   # pylint: disable=invalid-name
        """handle get request."""
        self.send_response(200)
        self.end_headers()
        client_ip, client_port = self.client_address
        dest_ip, dest_port = self.headers['Host'].split(':')

        self.wfile.write(DOC.format(**{
            'client_ip': client_ip,
            'client_port': client_port,
            'dest_ip': dest_ip,
            'dest_port': dest_port,
            'agent': self.headers['User-Agent'],
        }).encode())


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
