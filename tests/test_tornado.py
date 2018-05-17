import base64
import struct
import time

import pytest
import six

from tornado import ioloop
from tornado import gen

import consul
import consul.tornado


Check = consul.Check


@pytest.fixture
def loop():
    loop = ioloop.IOLoop()
    loop.make_current()
    return loop


def sleep(loop, s):
    result = gen.Future()
    loop.add_timeout(
        time.time()+s, lambda: result.set_result(None))
    return result


class TestConsul(object):
    def test_kv(self, loop, consul_port):
        @gen.coroutine
        def main():
            c = consul.tornado.Consul(port=consul_port)
            index, data = yield c.kv.get('foo')
            assert data is None
            response = yield c.kv.put('foo', 'bar')
            assert response is True
            index, data = yield c.kv.get('foo')
            assert data['Value'] == six.b('bar')
            loop.stop()
        loop.run_sync(main)

    def test_kv_binary(self, loop, consul_port):
        @gen.coroutine
        def main():
            c = consul.tornado.Consul(port=consul_port)
            yield c.kv.put('foo', struct.pack('i', 1000))
            index, data = yield c.kv.get('foo')
            assert struct.unpack('i', data['Value']) == (1000,)
            loop.stop()
        loop.run_sync(main)

    def test_kv_missing(self, loop, consul_port):
        c = consul.tornado.Consul(port=consul_port)

        @gen.coroutine
        def main():
            yield c.kv.put('index', 'bump')
            index, data = yield c.kv.get('foo')
            assert data is None
            index, data = yield c.kv.get('foo', index=index)
            assert data['Value'] == six.b('bar')
            loop.stop()

        @gen.coroutine
        def put():
            yield c.kv.put('foo', 'bar')

        loop.add_timeout(time.time()+(2.0/100), put)
        loop.run_sync(main)

    def test_kv_put_flags(self, loop, consul_port):
        @gen.coroutine
        def main():
            c = consul.tornado.Consul(port=consul_port)
            yield c.kv.put('foo', 'bar')
            index, data = yield c.kv.get('foo')
            assert data['Flags'] == 0

            response = yield c.kv.put('foo', 'bar', flags=50)
            assert response is True
            index, data = yield c.kv.get('foo')
            assert data['Flags'] == 50
            loop.stop()
        loop.run_sync(main)

    def test_kv_delete(self, loop, consul_port):
        @gen.coroutine
        def main():
            c = consul.tornado.Consul(port=consul_port)
            yield c.kv.put('foo1', '1')
            yield c.kv.put('foo2', '2')
            yield c.kv.put('foo3', '3')
            index, data = yield c.kv.get('foo', recurse=True)
            assert [x['Key'] for x in data] == ['foo1', 'foo2', 'foo3']

            response = yield c.kv.delete('foo2')
            assert response is True
            index, data = yield c.kv.get('foo', recurse=True)
            assert [x['Key'] for x in data] == ['foo1', 'foo3']
            response = yield c.kv.delete('foo', recurse=True)
            assert response is True
            index, data = yield c.kv.get('foo', recurse=True)
            assert data is None
            loop.stop()
        loop.run_sync(main)

    def test_kv_subscribe(self, loop, consul_port):
        c = consul.tornado.Consul(port=consul_port)

        @gen.coroutine
        def get():
            index, data = yield c.kv.get('foo')
            assert data is None
            index, data = yield c.kv.get('foo', index=index)
            assert data['Value'] == six.b('bar')
            loop.stop()

        @gen.coroutine
        def put():
            response = yield c.kv.put('foo', 'bar')
            assert response is True

        loop.add_timeout(time.time()+(1.0/100), put)
        loop.run_sync(get)

    def test_kv_encoding(self, loop, consul_port):
        @gen.coroutine
        def main():
            c = consul.tornado.Consul(port=consul_port)

            # test binary
            response = yield c.kv.put('foo', struct.pack('i', 1000))
            assert response is True
            index, data = yield c.kv.get('foo')
            assert struct.unpack('i', data['Value']) == (1000,)

            # test unicode
            response = yield c.kv.put('foo', u'bar')
            assert response is True
            index, data = yield c.kv.get('foo')
            assert data['Value'] == six.b('bar')

            # test empty-string comes back as `None`
            response = yield c.kv.put('foo', '')
            assert response is True
            index, data = yield c.kv.get('foo')
            assert data['Value'] is None

            # test None
            response = yield c.kv.put('foo', None)
            assert response is True
            index, data = yield c.kv.get('foo')
            assert data['Value'] is None

            # check unencoded values raises assert
            try:
                yield c.kv.put('foo', {1: 2})
            except AssertionError:
                raised = True
            assert raised

            loop.stop()
        loop.run_sync(main)

    def test_transaction(self, loop, consul_port):
        @gen.coroutine
        def main():
            c = consul.tornado.Consul(port=consul_port)
            value = base64.b64encode(b"1").decode("utf8")
            d = {"KV": {"Verb": "set", "Key": "asdf", "Value": value}}
            r = yield c.txn.put([d])
            assert r["Errors"] is None

            d = {"KV": {"Verb": "get", "Key": "asdf"}}
            r = yield c.txn.put([d])
            assert r["Results"][0]["KV"]["Value"] == value
            loop.stop()
        loop.run_sync(main)

    def test_agent_services(self, loop, consul_port):
        @gen.coroutine
        def main():
            c = consul.tornado.Consul(port=consul_port)
            services = yield c.agent.services()
            assert services == {}
            response = yield c.agent.service.register('foo')
            assert response is True
            services = yield c.agent.services()
            assert services == {
                'foo': {
                    'Port': 0,
                    'ID': 'foo',
                    'CreateIndex': 0,
                    'ModifyIndex': 0,
                    'EnableTagOverride': False,
                    'Service': 'foo',
                    'Tags': [],
                    'Address': ''}, }
            response = yield c.agent.service.deregister('foo')
            assert response is True
            services = yield c.agent.services()
            assert services == {}
            loop.stop()
        loop.run_sync(main)

    def test_catalog(self, loop, consul_port):
        c = consul.tornado.Consul(port=consul_port)

        @gen.coroutine
        def nodes():
            index, nodes = yield c.catalog.nodes()
            assert len(nodes) == 1
            current = nodes[0]

            index, nodes = yield c.catalog.nodes(index=index)
            nodes.remove(current)
            assert [x['Node'] for x in nodes] == ['n1']

            index, nodes = yield c.catalog.nodes(index=index)
            nodes.remove(current)
            assert [x['Node'] for x in nodes] == []
            loop.stop()

        @gen.coroutine
        def register():
            response = yield c.catalog.register('n1', '10.1.10.11')
            assert response is True
            yield sleep(loop, 50/1000.0)
            response = yield c.catalog.deregister('n1')
            assert response is True

        loop.add_timeout(time.time()+(1.0/100), register)
        loop.run_sync(nodes)

    def test_health_service(self, loop, consul_port):
        @gen.coroutine
        def main():
            c = consul.tornado.Consul(port=consul_port)

            # check there are no nodes for the service 'foo'
            index, nodes = yield c.health.service('foo')
            assert nodes == []

            # register two nodes, one with a long ttl, the other shorter
            yield c.agent.service.register(
                'foo', service_id='foo:1', check=Check.ttl('10s'))
            yield c.agent.service.register(
                'foo', service_id='foo:2', check=Check.ttl('100ms'))

            time.sleep(30/1000.0)

            # check the nodes show for the /health/service endpoint
            index, nodes = yield c.health.service('foo')
            assert [node['Service']['ID'] for node in nodes] == \
                ['foo:1', 'foo:2']

            # but that they aren't passing their health check
            index, nodes = yield c.health.service('foo', passing=True)
            assert nodes == []

            # ping the two node's health check
            yield c.agent.check.ttl_pass('service:foo:1')
            yield c.agent.check.ttl_pass('service:foo:2')

            time.sleep(50/1000.0)

            # both nodes are now available
            index, nodes = yield c.health.service('foo', passing=True)
            assert [node['Service']['ID'] for node in nodes] == \
                ['foo:1', 'foo:2']

            # wait until the short ttl node fails
            time.sleep(120/1000.0)

            # only one node available
            index, nodes = yield c.health.service('foo', passing=True)
            assert [node['Service']['ID'] for node in nodes] == ['foo:1']

            # ping the failed node's health check
            yield c.agent.check.ttl_pass('service:foo:2')

            time.sleep(30/1000.0)

            # check both nodes are available
            index, nodes = yield c.health.service('foo', passing=True)
            assert [node['Service']['ID'] for node in nodes] == \
                ['foo:1', 'foo:2']

            # deregister the nodes
            yield c.agent.service.deregister('foo:1')
            yield c.agent.service.deregister('foo:2')

            time.sleep(30/1000.0)

            index, nodes = yield c.health.service('foo')
            assert nodes == []

        loop.run_sync(main)

    def test_health_service_subscribe(self, loop, consul_port):
        c = consul.tornado.Consul(port=consul_port)

        class Config(object):
            pass

        config = Config()

        @gen.coroutine
        def monitor():
            yield c.agent.service.register(
                'foo', service_id='foo:1', check=Check.ttl('40ms'))
            index = None
            while True:
                index, nodes = yield c.health.service(
                    'foo', index=index, passing=True)
                config.nodes = [node['Service']['ID'] for node in nodes]

        @gen.coroutine
        def keepalive():
            # give the monitor a chance to register the service
            yield sleep(loop, 50/1000.0)
            assert config.nodes == []

            # ping the service's health check
            yield c.agent.check.ttl_pass('service:foo:1')
            yield sleep(loop, 30/1000.0)
            assert config.nodes == ['foo:1']

            # the service should fail
            yield sleep(loop, 60/1000.0)
            assert config.nodes == []

            yield c.agent.service.deregister('foo:1')
            loop.stop()

        loop.add_callback(monitor)
        loop.run_sync(keepalive)

    def test_session(self, loop, consul_port):
        c = consul.tornado.Consul(port=consul_port)

        @gen.coroutine
        def monitor():
            index, services = yield c.session.list()
            assert services == []
            yield sleep(loop, 20/1000.0)

            index, services = yield c.session.list(index=index)
            assert len(services)

            index, services = yield c.session.list(index=index)
            assert services == []
            loop.stop()

        @gen.coroutine
        def register():
            session_id = yield c.session.create()
            yield sleep(loop, 50/1000.0)
            response = yield c.session.destroy(session_id)
            assert response is True

        loop.add_timeout(time.time()+(1.0/100), register)
        loop.run_sync(monitor)

    def test_acl(self, loop, acl_consul):
        @gen.coroutine
        def main():
            c = consul.tornado.Consul(
                port=acl_consul.port, token=acl_consul.token)

            rules = """
                key "" {
                    policy = "read"
                }
                key "private/" {
                    policy = "deny"
                }
            """
            token = yield c.acl.create(rules=rules)

            try:
                yield c.acl.list(token=token)
            except consul.ACLPermissionDenied:
                raised = True
            assert raised

            destroyed = yield c.acl.destroy(token)
            assert destroyed is True
            loop.stop()
        loop.run_sync(main)
