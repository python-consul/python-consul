import subprocess
import tempfile
import socket
import shlex
import time
import json
import os

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


@pytest.yield_fixture(scope="module")
def consul():
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

    time.sleep(0.5)
    yield ports['http']
    p.terminate()


def test_core(consul):
    print
    print
    print consul


def test_foo(consul):
    print
    print
    print consul
