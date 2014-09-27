import time

from consul.fixture import consul_instance
from consul.fixture import consul_port

assert consul_instance and consul_port, "keep flake8 happy"

import consul
import consul.std


class TestHTTPClient(object):
    def test_uri(self):
        http = consul.std.HTTPClient()
        assert http.uri('/v1/kv') == 'http://127.0.0.1:8500/v1/kv'
        assert http.uri('/v1/kv', params={'index': 1}) == \
            'http://127.0.0.1:8500/v1/kv?index=1'


class TestConsul(object):
    def test_kv(self, consul_port):
        c = consul.Consul(port=consul_port)
        index, data = c.kv.get('foo')
        assert data is None
        assert c.kv.put('foo', 'bar') is True
        index, data = c.kv.get('foo')
        assert data['Value'] == 'bar'

    def test_agent_self(self, consul_port):
        c = consul.Consul(port=consul_port)
        assert c.agent.self().keys() == ['Member', 'Config']

    def test_agent_services(self, consul_port):
        c = consul.Consul(port=consul_port)
        assert c.agent.services() == {}
        assert c.agent.service.register('foo') is True
        assert c.agent.services() == {
            'foo': {'Port': 0, 'ID': 'foo', 'Service': 'foo', 'Tags': None}}
        assert c.agent.service.deregister('foo') is True
        assert c.agent.services() == {}

    def test_health_service(self, consul_port):
        c = consul.Consul(port=consul_port)

        # check there are no nodes for the service 'foo'
        index, nodes = c.health.service('foo')
        assert nodes == []

        # register two nodes, one with a long ttl, the other shorter
        c.agent.service.register('foo', service_id='foo:1', ttl='10s')
        c.agent.service.register('foo', service_id='foo:2', ttl='20ms')

        # check the nodes show for the /health/service endpoint
        index, nodes = c.health.service('foo')
        assert [node['Service']['ID'] for node in nodes] == ['foo:1', 'foo:2']

        # but that they aren't passing their health check
        index, nodes = c.health.service('foo', passing=True)
        assert nodes == []

        # ping the two node's health check
        c.health.check.ttl_pass('service:foo:1')
        c.health.check.ttl_pass('service:foo:2')

        # both nodes are now available
        index, nodes = c.health.service('foo', passing=True)
        assert [node['Service']['ID'] for node in nodes] == ['foo:1', 'foo:2']

        # wait until the short ttl node fails
        time.sleep(40/1000.0)

        # only one node available
        index, nodes = c.health.service('foo', passing=True)
        assert [node['Service']['ID'] for node in nodes] == ['foo:1']

        # ping the failed node's health check
        c.health.check.ttl_pass('service:foo:2')

        # check both nodes are available
        index, nodes = c.health.service('foo', passing=True)
        assert [node['Service']['ID'] for node in nodes] == ['foo:1', 'foo:2']

        # deregister the nodes
        c.agent.service.deregister('foo:1')
        c.agent.service.deregister('foo:2')

        index, nodes = c.health.service('foo')
        assert nodes == []
