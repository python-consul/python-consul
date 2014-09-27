import subprocess
import tempfile
import socket
import shlex
import time
import json
import os

import requests
import pytest
import py


def get_free_ports(num, host=None):
    if not host:
        host = '127.0.0.1'
    sockets = []
    ret = []
    for i in xrange(num):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((host, 0))
        ret.append(s.getsockname()[1])
        sockets.append(s)
    for s in sockets:
        s.close()
    return ret


@pytest.yield_fixture(scope="session")
def consul_instance():
    ports = dict(zip(
        ['http', 'rpc', 'serf_lan', 'serf_wan', 'server', 'dns'],
        get_free_ports(5) + [-1]))

    tmpdir = py.path.local(tempfile.mkdtemp())
    tmpdir.join('ports.json').write(json.dumps({'ports': ports}))
    tmpdir.chdir()

    bin = os.path.join(os.path.dirname(__file__), '../bin/consul')
    command = """
        {bin} agent -server -bootstrap -config-dir=. -data-dir=./data
    """.format(bin=bin).strip()
    command = shlex.split(command)

    p = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # wait for consul instance to bootstrap
    base_uri = 'http://127.0.0.1:%s/v1/' % ports['http']

    while True:
        time.sleep(0.1)
        response = requests.get(base_uri + 'status/leader')
        if response.text.strip() != '""':
            break

    requests.put(base_uri + 'agent/service/register', data='{"name": "foo"}')

    while True:
        # wait for consul instance to bootstrap
        time.sleep(0.1)
        response = requests.get(base_uri + 'health/service/foo')
        if response.text.strip() != '[]':
            break

    requests.get(base_uri + 'agent/service/deregister/foo')
    # phew

    yield ports['http']
    p.terminate()


@pytest.yield_fixture
def consul_port(consul_instance):
    yield consul_instance
