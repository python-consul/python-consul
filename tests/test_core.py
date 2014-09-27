import subprocess
import tempfile
import inspect
import socket
import shlex
import time
import uuid
import json
import os

import pytest
import py

import consul
import consul.core


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
def consul_port():
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

    time.sleep(2)
    yield ports['http']
    p.terminate()


class TestBuild(object):
    def test_build(self):
        api = consul.core.build_v1(None)

        get = api.kv.get
        assert get.__name__ == 'get'
        spec = inspect.getargspec(get)
        assert spec.args == ['key', 'index', 'recurse']
        assert spec.defaults == (None, None)
        assert spec.varargs is None
        assert spec.keywords is None

        put = api.kv.put
        assert put.__name__ == 'put'
        spec = inspect.getargspec(put)
        assert spec.args == ['key', 'value']
        assert spec.defaults is None
        assert spec.varargs is None
        assert spec.keywords is None

        self = api.agent.self
        assert self.__name__ == 'self'
        spec = inspect.getargspec(self)
        assert spec.args == []
        assert spec.defaults is None
        assert spec.varargs is None
        assert spec.keywords is None

    def test_kv(self):
        class HTTPClient(object):
            def get(self, callback, path, params=None, data=None):
                return callback, path, params, data

        api = consul.core.build_v1(HTTPClient())

        callback, path, params, _ = api.kv.get('foo', recurse=True)
        assert callback == consul.core.v1_callbacks.kv_get
        assert path == '/v1/kv/foo'
        assert params == {'recurse': '1'}

    def test_agent_self(self):
        class HTTPClient(object):
            def get(self, callback, path, params=None, data=None):
                return callback, path, params, data

        api = consul.core.build_v1(HTTPClient())
        _, path, _, _ = api.agent.self()
        assert path == '/v1/agent/self'


class TestCore(object):
    def test_kv(self, consul_port):
        c = consul.Consul(port=consul_port)
        key = uuid.uuid4().hex
        index, data = c.kv.get(key)
        assert data is None
        assert c.kv.put(key, 'bar') is True
        index, data = c.kv.get(key)
        assert data['Value'] == 'bar'

    def test_agent_self(self, consul_port):
        c = consul.Consul(port=consul_port)
        assert set(c.agent.self().keys()) == set(['Member', 'Config'])
