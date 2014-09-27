import time

from tornado import ioloop
from tornado import gen

import pytest

import consul.tornado


@pytest.fixture
def loop():
    loop = ioloop.IOLoop()
    loop.make_current()
    return loop


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
            assert data['Value'] == 'bar'
            loop.stop()
        loop.run_sync(main)

    def test_kv_subscribe(self, loop, consul_port):
        c = consul.tornado.Consul(port=consul_port)

        @gen.coroutine
        def get():
            index, data = yield c.kv.get('foo')
            assert data is None
            index, data = yield c.kv.get('foo', index=index)
            assert data['Value'] == 'bar'
            loop.stop()

        @gen.coroutine
        def put():
            response = yield c.kv.put('foo', 'bar')
            assert response is True

        loop.add_timeout(time.time()+(1.0/100), put)
        loop.run_sync(get)

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
                    'Port': 0, 'ID': 'foo', 'Service': 'foo', 'Tags': None}}
            response = yield c.agent.service.deregister('foo')
            assert response is True
            services = yield c.agent.services()
            assert services == {}
            loop.stop()
        loop.run_sync(main)

    def test_health_service(self, loop, consul_port):
        @gen.coroutine
        def main():
            c = consul.tornado.Consul(port=consul_port)

            # check there are no nodes for the service 'foo'
            index, nodes = yield c.health.service('foo')
            assert nodes == []

            # register two nodes, one with a long ttl, the other shorter
            yield c.agent.service.register(
                'foo', service_id='foo:1', ttl='10s')
            yield c.agent.service.register(
                'foo', service_id='foo:2', ttl='20ms')

            # check the nodes show for the /health/service endpoint
            index, nodes = yield c.health.service('foo')
            assert [node['Service']['ID'] for node in nodes] == \
                ['foo:1', 'foo:2']

            # but that they aren't passing their health check
            index, nodes = yield c.health.service('foo', passing=True)
            assert nodes == []

            # ping the two node's health check
            yield c.health.check.ttl_pass('service:foo:1')
            yield c.health.check.ttl_pass('service:foo:2')

            # both nodes are now available
            index, nodes = yield c.health.service('foo', passing=True)
            assert [node['Service']['ID'] for node in nodes] == \
                ['foo:1', 'foo:2']

            # wait until the short ttl node fails
            time.sleep(40/1000.0)

            # only one node available
            index, nodes = yield c.health.service('foo', passing=True)
            assert [node['Service']['ID'] for node in nodes] == ['foo:1']

            # ping the failed node's health check
            yield c.health.check.ttl_pass('service:foo:2')

            # check both nodes are available
            index, nodes = yield c.health.service('foo', passing=True)
            assert [node['Service']['ID'] for node in nodes] == \
                ['foo:1', 'foo:2']

            # deregister the nodes
            yield c.agent.service.deregister('foo:1')
            yield c.agent.service.deregister('foo:2')

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
                'foo', service_id='foo:1', ttl='20ms')
            index = None
            while True:
                index, nodes = yield c.health.service(
                    'foo', index=index, passing=True)
                config.nodes = [node['Service']['ID'] for node in nodes]

        def sleep(s):
            result = gen.Future()
            loop.add_timeout(
                time.time()+s, lambda: result.set_result(None))
            return result

        @gen.coroutine
        def keepalive():
            # give the monitor a chance to register the service
            yield sleep(50/1000.0)
            assert config.nodes == []

            # ping the service's health check
            yield c.health.check.ttl_pass('service:foo:1')
            yield sleep(10/1000.0)
            assert config.nodes == ['foo:1']

            # the service should fail
            yield sleep(20/1000.0)
            assert config.nodes == []

            yield c.agent.service.deregister('foo:1')
            loop.stop()

        loop.add_callback(monitor)
        loop.run_sync(keepalive)
