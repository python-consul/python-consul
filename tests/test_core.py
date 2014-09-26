import subprocess
import tempfile
import inspect
import socket
import shlex
import time
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


class TestAPI(object):
    def test_api(self):
        api = consul.core.API()

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

    def test_set_http(self):
        class HTTPClient(consul.core.HTTPClient):
            def get(self, callback, uri, params=None, data=None):
                assert callback == consul.core.v1_callbacks.kv_get
                assert uri == 'http://127.0.0.1:8500/v1/kv/foo'
                return 23

        http = HTTPClient('127.0.0.1', 8500)
        api = consul.core.API()
        api.set_http(http)
        assert api.kv.get('foo') == 23


class TestCore(object):
    def test_kv(self, consul_port):
        print
        print
        c = consul.connect(port=consul_port)

        print c.kv.get('foo')
        print c.kv.put('foo', 'bar')
        print c.kv.get('foo')
