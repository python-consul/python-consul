import collections
import subprocess
import platform
import sys
import tempfile
import socket
import shlex
import uuid
import time
import json
import os

import requests
import pytest
import py

collect_ignore = []

if sys.version_info[0] < 3:
    p = os.path.join(os.path.dirname(__file__), 'test_aio.py')
    collect_ignore.append(p)


if sys.version_info[0] == 2 and sys.version_info[1] < 7:
    p = os.path.join(os.path.dirname(__file__), 'test_twisted.py')
    collect_ignore.append(p)
    p = os.path.join(os.path.dirname(__file__), 'test_tornado.py')
    collect_ignore.append(p)
else:
    pytest_plugins = "pytest_twisted"


def get_free_ports(num, host=None):
    if not host:
        host = '127.0.0.1'
    sockets = []
    ret = []
    for i in range(num):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((host, 0))
        ret.append(s.getsockname()[1])
        sockets.append(s)
    for s in sockets:
        s.close()
    return ret


def start_consul_instance(acl_master_token=None):
    """
    starts a consul instance. if acl_master_token is None, acl will be disabled
    for this server, otherwise it will be enabled and the master token will be
    set to the supplied token

    returns: a tuple of the instances process object and the http port the
             instance is listening on
    """
    ports = dict(zip(
        ['http', 'serf_lan', 'serf_wan', 'server', 'dns'],
        get_free_ports(4) + [-1]))

    config = {'ports': ports, 'performance': {'raft_multiplier': 1},
              'enable_script_checks': True}
    if acl_master_token:
        config['acl_datacenter'] = 'dc1'
        config['acl_master_token'] = acl_master_token

    tmpdir = py.path.local(tempfile.mkdtemp())
    tmpdir.join('config.json').write(json.dumps(config))
    tmpdir.chdir()

    (system, node, release, version, machine, processor) = platform.uname()
    if system == 'Darwin':
        postfix = 'osx'
    else:
        postfix = 'linux64'
    bin = os.path.join(os.path.dirname(__file__), 'consul.'+postfix)
    command = '{bin} agent -dev' \
              ' -bind=127.0.0.1' \
              ' -config-dir=.'
    command = command.format(bin=bin).strip()
    command = shlex.split(command)

    p = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # wait for consul instance to bootstrap
    base_uri = 'http://127.0.0.1:%s/v1/' % ports['http']

    while True:
        time.sleep(0.1)
        try:
            response = requests.get(base_uri + 'status/leader')
        except requests.ConnectionError:
            continue
        print(response.text)
        if response.text.strip() != '""':
            break

    requests.put(base_uri + 'agent/service/register', data='{"name": "foo"}')

    while True:
        response = requests.get(base_uri + 'health/service/foo')
        if response.text.strip() != '[]':
            break
        time.sleep(0.1)

    requests.put(base_uri + 'agent/service/deregister/foo')
    # phew
    time.sleep(2)
    return p, ports['http']


@pytest.yield_fixture(scope="module")
def consul_instance():
    p, port = start_consul_instance()
    yield port
    p.terminate()


@pytest.yield_fixture
def consul_port(consul_instance):
    yield consul_instance
    # remove all data from the instance, to have a clean start
    base_uri = 'http://127.0.0.1:%s/v1/' % consul_instance
    requests.delete(base_uri + 'kv/?recurse=1')


@pytest.yield_fixture(scope="module")
def acl_consul_instance():
    acl_master_token = uuid.uuid4().hex
    p, port = start_consul_instance(acl_master_token=acl_master_token)
    yield port, acl_master_token
    p.terminate()


@pytest.yield_fixture
def acl_consul(acl_consul_instance):
    ACLConsul = collections.namedtuple('ACLConsul', ['port', 'token'])
    port, token = acl_consul_instance
    yield ACLConsul(port, token)
    # remove all data from the instance, to have a clean start
    base_uri = 'http://127.0.0.1:%s/v1/' % port
    requests.delete(base_uri + 'kv/?recurse=1')
