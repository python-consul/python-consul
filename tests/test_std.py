import operator
import struct
import time

import pytest
import six

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
        assert data['Value'] == six.b('bar')

    def test_kv_wait(self, consul_port):
        c = consul.Consul(port=consul_port)
        assert c.kv.put('foo', 'bar') is True
        index, data = c.kv.get('foo')
        check, data = c.kv.get('foo', index=index, wait='20ms')
        assert index == check

    def test_kv_encoding(self, consul_port):
        c = consul.Consul(port=consul_port)

        # test binary
        c.kv.put('foo', struct.pack('i', 1000))
        index, data = c.kv.get('foo')
        assert struct.unpack('i', data['Value']) == (1000,)

        # test unicode
        c.kv.put('foo', u'bar')
        index, data = c.kv.get('foo')
        assert data['Value'] == six.b('bar')

        # test None
        c.kv.put('foo', None)
        index, data = c.kv.get('foo')
        assert data['Value'] is None

        # check unencoded values raises assert
        pytest.raises(AssertionError, c.kv.put, 'foo', {1: 2})

    def test_kv_put_cas(self, consul_port):
        c = consul.Consul(port=consul_port)
        assert c.kv.put('foo', 'bar', cas=50) is False
        assert c.kv.put('foo', 'bar', cas=0) is True
        index, data = c.kv.get('foo')

        assert c.kv.put('foo', 'bar2', cas=data['ModifyIndex']-1) is False
        assert c.kv.put('foo', 'bar2', cas=data['ModifyIndex']) is True
        index, data = c.kv.get('foo')
        assert data['Value'] == six.b('bar2')

    def test_kv_put_flags(self, consul_port):
        c = consul.Consul(port=consul_port)
        c.kv.put('foo', 'bar')
        index, data = c.kv.get('foo')
        assert data['Flags'] == 0

        assert c.kv.put('foo', 'bar', flags=50) is True
        index, data = c.kv.get('foo')
        assert data['Flags'] == 50

    def test_kv_recurse(self, consul_port):
        c = consul.Consul(port=consul_port)
        index, data = c.kv.get('foo/', recurse=True)
        assert data is None

        c.kv.put('foo/', None)
        index, data = c.kv.get('foo/', recurse=True)
        assert len(data) == 1

        c.kv.put('foo/bar1', '1')
        c.kv.put('foo/bar2', '2')
        c.kv.put('foo/bar3', '3')
        index, data = c.kv.get('foo/', recurse=True)
        assert [x['Key'] for x in data] == [
            'foo/bar1', 'foo/bar2', 'foo/bar3', 'foo/']
        assert [x['Value'] for x in data] == [
            six.b('1'), six.b('2'), six.b('3'), None]

    def test_kv_delete(self, consul_port):
        c = consul.Consul(port=consul_port)
        c.kv.put('foo1', '1')
        c.kv.put('foo2', '2')
        c.kv.put('foo3', '3')
        index, data = c.kv.get('foo', recurse=True)
        assert [x['Key'] for x in data] == ['foo1', 'foo2', 'foo3']

        assert c.kv.delete('foo2') is True
        index, data = c.kv.get('foo', recurse=True)
        assert [x['Key'] for x in data] == ['foo1', 'foo3']
        assert c.kv.delete('foo', recurse=True) is True
        index, data = c.kv.get('foo', recurse=True)
        assert data is None

    def test_kv_delete_cas(self, consul_port):
        c = consul.Consul(port=consul_port)

        c.kv.put('foo', 'bar')
        index, data = c.kv.get('foo')

        assert c.kv.delete('foo', cas=data['ModifyIndex']-1) is False
        assert c.kv.get('foo') == (index, data)

        assert c.kv.delete('foo', cas=data['ModifyIndex']) is True
        index, data = c.kv.get('foo')
        assert data is None

    def test_kv_acquire_release(self, consul_port):
        c = consul.Consul(port=consul_port)

        pytest.raises(
            consul.ConsulException, c.kv.put, 'foo', 'bar', acquire='foo')

        s1 = c.session.create()
        s2 = c.session.create()

        assert c.kv.put('foo', '1', acquire=s1) is True
        assert c.kv.put('foo', '2', acquire=s2) is False
        assert c.kv.put('foo', '1', acquire=s1) is False
        assert c.kv.put('foo', '1', release='foo') is False
        assert c.kv.put('foo', '2', release=s2) is False
        assert c.kv.put('foo', '2', release=s1) is True

        c.session.destroy(s1)
        c.session.destroy(s2)

    def test_kv_keys_only(self, consul_port):
        c = consul.Consul(port=consul_port)

        assert c.kv.put('bar', '4') is True
        assert c.kv.put('base/foo', '1') is True
        assert c.kv.put('base/base/foo', '5') is True

        index, data = c.kv.get('base/', keys=True, separator='/')
        assert data == ['base/base/', 'base/foo']

    def test_event(self, consul_port):
        c = consul.Consul(port=consul_port)

        assert c.event.fire("fooname", "foobody")
        index, events = c.event.list()
        assert [x['Name'] == 'fooname' for x in events]
        assert [x['Payload'] == 'foobody' for x in events]

    def test_event_targeted(self, consul_port):
        c = consul.Consul(port=consul_port)

        assert c.event.fire("fooname", "foobody")
        index, events = c.event.list(name="othername")
        assert events == []

        index, events = c.event.list(name="fooname")
        assert [x['Name'] == 'fooname' for x in events]
        assert [x['Payload'] == 'foobody' for x in events]

    def test_agent_checks(self, consul_port):
        c = consul.Consul(port=consul_port)

        def verify_and_dereg_check(check_id):
            assert set(c.agent.checks().keys()) == set([check_id])
            assert c.agent.check.deregister(check_id) is True
            assert set(c.agent.checks().keys()) == set([])

        def verify_check_status(check_id, status, notes=None):
            checks = c.agent.checks()
            assert checks[check_id]['Status'] == status
            if notes:
                assert checks[check_id]['Output'] == notes

        # test setting notes on a check
        c.agent.check.register('check', ttl='1s', notes='foo')
        assert c.agent.checks()['check']['Notes'] == 'foo'
        c.agent.check.deregister('check')

        assert set(c.agent.checks().keys()) == set([])
        assert c.agent.check.register(
            'script_check', script='/bin/true', interval=10) is True
        verify_and_dereg_check('script_check')

        assert c.agent.check.register('check name',
                                      check_id='check_id',
                                      script='/bin/true', interval=10) is True
        verify_and_dereg_check('check_id')

        http_addr = "http://127.0.0.1:{0}".format(consul_port)
        assert c.agent.check.register(
            'http_check', http=http_addr, interval='10ms') is True
        time.sleep(1)
        verify_check_status('http_check', 'passing')
        verify_and_dereg_check('http_check')

        assert c.agent.check.register(
            'http_timeout_check',
            http=http_addr,
            timeout='2s',
            interval='100ms') is True
        verify_and_dereg_check('http_timeout_check')

        assert c.agent.check.register('ttl_check', ttl='100ms') is True

        assert c.agent.check.ttl_warn('ttl_check') is True
        verify_check_status('ttl_check', 'warning')
        assert c.agent.check.ttl_warn(
            'ttl_check', notes='its not quite right') is True
        verify_check_status('ttl_check', 'warning', 'its not quite right')

        assert c.agent.check.ttl_fail('ttl_check') is True
        verify_check_status('ttl_check', 'critical')
        assert c.agent.check.ttl_fail(
            'ttl_check', notes='something went boink!') is True
        verify_check_status(
            'ttl_check', 'critical', notes='something went boink!')

        assert c.agent.check.ttl_pass('ttl_check') is True
        verify_check_status('ttl_check', 'passing')
        assert c.agent.check.ttl_pass(
            'ttl_check', notes='all hunky dory!') is True
        verify_check_status('ttl_check', 'passing', notes='all hunky dory!')
        # wait for ttl to expire
        time.sleep(120/1000.0)
        verify_check_status('ttl_check', 'critical')
        verify_and_dereg_check('ttl_check')

        pytest.raises(
            AssertionError,
            c.agent.check.register, 'check_id', script='/bin/true', ttl=50)
        pytest.raises(
            AssertionError,
            c.agent.check.register, 'check_id', interval=10, ttl=50)

    def test_agent_checks_service_id(self, consul_port):
        c = consul.Consul(port=consul_port)
        c.agent.service.register('foo1')

        time.sleep(40/1000.0)

        index, nodes = c.health.service('foo1')
        assert [node['Service']['ID'] for node in nodes] == ['foo1']

        c.agent.check.register('foo', service_id='foo1', ttl='100ms')

        time.sleep(40/1000.0)

        index, nodes = c.health.service('foo1')
        assert [check['ServiceID'] for node in nodes for check in node['Checks']] == \
            ['foo1', '']
        assert [check['CheckID'] for node in nodes for check in node['Checks']] == \
            ['foo', 'serfHealth']

        # Clean up tasks
        assert c.agent.check.deregister('foo') is True

        time.sleep(40/1000.0)

        assert c.agent.service.deregister('foo1') is True

        time.sleep(40/1000.0)

    def test_agent_register_check_no_service_id(self, consul_port):
        c = consul.Consul(port=consul_port)
        index, nodes = c.health.service("foo1")
        assert nodes == []

        assert c.agent.check.register('foo', service_id='foo1', ttl='100ms') is \
            False

        time.sleep(40/1000.0)

        assert c.agent.checks() == {}

        # Cleanup tasks
        c.agent.check.deregister('foo')

        time.sleep(40/1000.0)

    def test_agent_members(self, consul_port):
        c = consul.Consul(port=consul_port)
        members = c.agent.members()
        for x in members:
            assert x['Status'] == 1
            assert not x['Name'] is None
            assert not x['Tags'] is None
        assert c.agent.self()['Member'] in members

        wan_members = c.agent.members(wan=True)
        for x in wan_members:
            assert 'dc1' in x['Name']

    def test_agent_self(self, consul_port):
        c = consul.Consul(port=consul_port)
        assert set(c.agent.self().keys()) == set(['Member', 'Config'])

    def test_agent_services(self, consul_port):
        c = consul.Consul(port=consul_port)
        assert set(c.agent.services().keys()) == set(['consul'])
        assert c.agent.service.register('foo') is True
        assert set(c.agent.services().keys()) == set(['consul', 'foo'])
        assert c.agent.service.deregister('foo') is True
        assert set(c.agent.services().keys()) == set(['consul'])

        # test address param
        assert c.agent.service.register('foo', address='10.10.10.1') is True
        assert [
            v['Address'] for k, v in c.agent.services().iteritems()
            if k == 'foo'][0] == '10.10.10.1'
        assert c.agent.service.deregister('foo') is True

    def test_catalog(self, consul_port):
        c = consul.Consul(port=consul_port)

        # grab the node our server created, so we can ignore it
        _, nodes = c.catalog.nodes()
        assert len(nodes) == 1
        current = nodes[0]

        # test catalog.datacenters
        assert c.catalog.datacenters() == ['dc1']

        # test catalog.register
        pytest.raises(
            consul.ConsulException,
            c.catalog.register, 'foo', '10.1.10.11', dc='dc2')

        assert c.catalog.register(
            'n1',
            '10.1.10.11',
            service={'service': 's1'},
            check={'name': 'c1'}) is True
        assert c.catalog.register(
            'n1', '10.1.10.11', service={'service': 's2'}) is True
        assert c.catalog.register(
            'n2', '10.1.10.12',
            service={'service': 's1', 'tags': ['master']}) is True

        # test catalog.nodes
        pytest.raises(consul.ConsulException, c.catalog.nodes, dc='dc2')
        _, nodes = c.catalog.nodes()
        nodes.remove(current)
        assert [x['Node'] for x in nodes] == ['n1', 'n2']

        # test catalog.services
        pytest.raises(consul.ConsulException, c.catalog.services, dc='dc2')
        _, services = c.catalog.services()
        assert services == {'s1': [u'master'], 's2': [], 'consul': []}

        # test catalog.node
        pytest.raises(consul.ConsulException, c.catalog.node, 'n1', dc='dc2')
        _, node = c.catalog.node('n1')
        assert set(node['Services'].keys()) == set(['s1', 's2'])
        _, node = c.catalog.node('n3')
        assert node is None

        # test catalog.service
        pytest.raises(
            consul.ConsulException, c.catalog.service, 's1', dc='dc2')
        _, nodes = c.catalog.service('s1')
        assert set([x['Node'] for x in nodes]) == set(['n1', 'n2'])
        _, nodes = c.catalog.service('s1', tag='master')
        assert set([x['Node'] for x in nodes]) == set(['n2'])

        # test catalog.deregister
        pytest.raises(
            consul.ConsulException, c.catalog.deregister, 'n2', dc='dc2')
        assert c.catalog.deregister('n1', check_id='c1') is True
        assert c.catalog.deregister('n2', service_id='s1') is True
        # check the nodes weren't removed
        _, nodes = c.catalog.nodes()
        nodes.remove(current)
        assert [x['Node'] for x in nodes] == ['n1', 'n2']
        # check n2's s1 service was removed though
        _, nodes = c.catalog.service('s1')
        assert set([x['Node'] for x in nodes]) == set(['n1'])

        # cleanup
        assert c.catalog.deregister('n1') is True
        assert c.catalog.deregister('n2') is True
        _, nodes = c.catalog.nodes()
        nodes.remove(current)
        assert [x['Node'] for x in nodes] == []

    def test_health_service(self, consul_port):
        c = consul.Consul(port=consul_port)

        # check there are no nodes for the service 'foo'
        index, nodes = c.health.service('foo')
        assert nodes == []

        # register two nodes, one with a long ttl, the other shorter
        c.agent.service.register(
            'foo', service_id='foo:1', ttl='10s', tags=['tag:foo:1'])
        c.agent.service.register('foo', service_id='foo:2', ttl='100ms')

        time.sleep(40/1000.0)

        # check the nodes show for the /health/service endpoint
        index, nodes = c.health.service('foo')
        assert [node['Service']['ID'] for node in nodes] == ['foo:1', 'foo:2']

        # but that they aren't passing their health check
        index, nodes = c.health.service('foo', passing=True)
        assert nodes == []

        # ping the two node's health check
        c.agent.check.ttl_pass('service:foo:1')
        c.agent.check.ttl_pass('service:foo:2')

        time.sleep(40/1000.0)

        # both nodes are now available
        index, nodes = c.health.service('foo', passing=True)
        assert [node['Service']['ID'] for node in nodes] == ['foo:1', 'foo:2']

        # wait until the short ttl node fails
        time.sleep(120/1000.0)

        # only one node available
        index, nodes = c.health.service('foo', passing=True)
        assert [node['Service']['ID'] for node in nodes] == ['foo:1']

        # ping the failed node's health check
        c.agent.check.ttl_pass('service:foo:2')

        time.sleep(40/1000.0)

        # check both nodes are available
        index, nodes = c.health.service('foo', passing=True)
        assert [node['Service']['ID'] for node in nodes] == ['foo:1', 'foo:2']

        # check that tag works
        index, nodes = c.health.service('foo', tag='tag:foo:1')
        assert [node['Service']['ID'] for node in nodes] == ['foo:1']

        # deregister the nodes
        c.agent.service.deregister('foo:1')
        c.agent.service.deregister('foo:2')

        time.sleep(40/1000.0)

        index, nodes = c.health.service('foo')
        assert nodes == []

    def test_health_state(self, consul_port):
        c = consul.Consul(port=consul_port)

        # The empty string is for the Serf Health Status check, which has an
        # empty ServiceID
        index, nodes = c.health.state('any')
        assert [node['ServiceID'] for node in nodes] == ['']

        # register two nodes, one with a long ttl, the other shorter
        c.agent.service.register('foo', service_id='foo:1', ttl='10s')
        c.agent.service.register('foo', service_id='foo:2', ttl='100ms')

        time.sleep(40/1000.0)

        # check the nodes show for the /health/state/any endpoint
        index, nodes = c.health.state('any')
        assert [node['ServiceID'] for node in nodes] == ['', 'foo:1', 'foo:2']

        # but that they aren't passing their health check
        index, nodes = c.health.state('passing')
        assert [node['ServiceID'] for node in nodes] != 'foo'

        # ping the two node's health check
        c.agent.check.ttl_pass('service:foo:1')
        c.agent.check.ttl_pass('service:foo:2')

        time.sleep(40/1000.0)

        # both nodes are now available
        index, nodes = c.health.state('passing')
        assert [node['ServiceID'] for node in nodes] == ['', 'foo:1', 'foo:2']

        # wait until the short ttl node fails
        time.sleep(120/1000.0)

        # only one node available
        index, nodes = c.health.state('passing')
        assert [node['ServiceID'] for node in nodes] == ['', 'foo:1']

        # ping the failed node's health check
        c.agent.check.ttl_pass('service:foo:2')

        time.sleep(40/1000.0)

        # check both nodes are available
        index, nodes = c.health.state('passing')
        assert [node['ServiceID'] for node in nodes] == ['', 'foo:1', 'foo:2']

        # deregister the nodes
        c.agent.service.deregister('foo:1')
        c.agent.service.deregister('foo:2')

        time.sleep(40/1000.0)

        index, nodes = c.health.state('any')
        assert [node['ServiceID'] for node in nodes] == ['']

    def test_session(self, consul_port):
        c = consul.Consul(port=consul_port)

        # session.create
        pytest.raises(consul.ConsulException, c.session.create, node='n2')
        pytest.raises(consul.ConsulException, c.session.create, dc='dc2')
        session_id = c.session.create('my-session')

        # session.list
        pytest.raises(consul.ConsulException, c.session.list, dc='dc2')
        _, sessions = c.session.list()
        assert [x['Name'] for x in sessions] == ['my-session']

        # session.info
        pytest.raises(
            consul.ConsulException, c.session.info, session_id, dc='dc2')
        index, session = c.session.info('foo')
        assert session is None
        index, session = c.session.info(session_id)
        assert session['Name'] == 'my-session'

        # session.node
        node = session['Node']
        pytest.raises(
            consul.ConsulException, c.session.node, node, dc='dc2')
        _, sessions = c.session.node(node)
        assert [x['Name'] for x in sessions] == ['my-session']

        # session.destroy
        pytest.raises(
            consul.ConsulException, c.session.destroy, session_id, dc='dc2')
        assert c.session.destroy(session_id) is True
        _, sessions = c.session.list()
        assert sessions == []

    def test_session_delete_ttl_renew(self, consul_port):
        c = consul.Consul(port=consul_port)

        s = c.session.create(behavior='delete', ttl=20)

        # attempt to renew an unknown session
        pytest.raises(consul.NotFound, c.session.renew, 'foo')

        session = c.session.renew(s)
        assert session['Behavior'] == 'delete'
        assert session['TTL'] == '20s'

        # trying out the behavior
        assert c.kv.put('foo', '1', acquire=s) is True
        index, data = c.kv.get('foo')
        assert data['Value'] == six.b('1')

        c.session.destroy(s)
        index, data = c.kv.get('foo')
        assert data is None

    def test_acl_disabled(self, consul_port):
        c = consul.Consul(port=consul_port)
        pytest.raises(consul.ACLDisabled, c.acl.list)
        pytest.raises(consul.ACLDisabled, c.acl.info, 'foo')
        pytest.raises(consul.ACLDisabled, c.acl.create)
        pytest.raises(consul.ACLDisabled, c.acl.update, 'foo')
        pytest.raises(consul.ACLDisabled, c.acl.clone, 'foo')
        pytest.raises(consul.ACLDisabled, c.acl.destroy, 'foo')

    def test_acl_permission_denied(self, acl_consul):
        c = consul.Consul(port=acl_consul.port)
        pytest.raises(consul.ACLPermissionDenied, c.acl.list)
        pytest.raises(consul.ACLPermissionDenied, c.acl.create)
        pytest.raises(consul.ACLPermissionDenied, c.acl.update, 'anonymous')
        pytest.raises(consul.ACLPermissionDenied, c.acl.clone, 'anonymous')
        pytest.raises(consul.ACLPermissionDenied, c.acl.destroy, 'anonymous')

    def test_acl_explict_token_use(self, acl_consul):
        c = consul.Consul(port=acl_consul.port)
        master_token = acl_consul.token

        acls = c.acl.list(token=master_token)
        assert set([x['ID'] for x in acls]) == \
            set(['anonymous', master_token])

        assert c.acl.info('foo') is None
        compare = [c.acl.info(master_token), c.acl.info('anonymous')]
        compare.sort(key=operator.itemgetter('ID'))
        assert acls == compare

        rules = """
            key "" {
                policy = "read"
            }
            key "private/" {
                policy = "deny"
            }
        """

        token = c.acl.create(rules=rules, token=master_token)
        assert c.acl.info(token)['Rules'] == rules

        token2 = c.acl.clone(token, token=master_token)
        assert c.acl.info(token2)['Rules'] == rules

        assert c.acl.update(token2, name='Foo', token=master_token) == token2
        assert c.acl.info(token2)['Name'] == 'Foo'

        assert c.acl.destroy(token2, token=master_token) is True
        assert c.acl.info(token2) is None

        c.kv.put('foo', 'bar')
        c.kv.put('private/foo', 'bar')

        assert c.kv.get('foo', token=token)[1]['Value'] == six.b('bar')
        pytest.raises(
            consul.ACLPermissionDenied, c.kv.put, 'foo', 'bar2', token=token)
        pytest.raises(
            consul.ACLPermissionDenied, c.kv.delete, 'foo', token=token)

        assert c.kv.get('private/foo')[1]['Value'] == six.b('bar')
        assert c.kv.get('private/foo', token=token)[1] is None
        pytest.raises(
            consul.ACLPermissionDenied,
            c.kv.put, 'private/foo', 'bar2', token=token)
        pytest.raises(
            consul.ACLPermissionDenied,
            c.kv.delete, 'private/foo', token=token)

        # clean up
        c.acl.destroy(token, token=master_token)
        acls = c.acl.list(token=master_token)
        assert set([x['ID'] for x in acls]) == \
            set(['anonymous', master_token])

    def test_acl_implicit_token_use(self, acl_consul):
        # configure client to use the master token by default
        c = consul.Consul(port=acl_consul.port, token=acl_consul.token)
        master_token = acl_consul.token

        acls = c.acl.list()
        assert set([x['ID'] for x in acls]) == \
            set(['anonymous', master_token])

        assert c.acl.info('foo') is None
        compare = [c.acl.info(master_token), c.acl.info('anonymous')]
        compare.sort(key=operator.itemgetter('ID'))
        assert acls == compare

        rules = """
            key "" {
                policy = "read"
            }
            key "private/" {
                policy = "deny"
            }
        """
        token = c.acl.create(rules=rules)
        assert c.acl.info(token)['Rules'] == rules

        token2 = c.acl.clone(token)
        assert c.acl.info(token2)['Rules'] == rules

        assert c.acl.update(token2, name='Foo') == token2
        assert c.acl.info(token2)['Name'] == 'Foo'

        assert c.acl.destroy(token2) is True
        assert c.acl.info(token2) is None

        c.kv.put('foo', 'bar')
        c.kv.put('private/foo', 'bar')

        c_limited = consul.Consul(port=acl_consul.port, token=token)
        assert c_limited.kv.get('foo')[1]['Value'] == six.b('bar')
        pytest.raises(
            consul.ACLPermissionDenied, c_limited.kv.put, 'foo', 'bar2')
        pytest.raises(
            consul.ACLPermissionDenied, c_limited.kv.delete, 'foo')

        assert c.kv.get('private/foo')[1]['Value'] == six.b('bar')
        assert c_limited.kv.get('private/foo')[1] is None
        pytest.raises(
            consul.ACLPermissionDenied,
            c_limited.kv.put, 'private/foo', 'bar2')
        pytest.raises(
            consul.ACLPermissionDenied,
            c_limited.kv.delete, 'private/foo')

        # check we can override the client's default token
        assert c.kv.get('private/foo', token=token)[1] is None
        pytest.raises(
            consul.ACLPermissionDenied,
            c.kv.put, 'private/foo', 'bar2', token=token)
        pytest.raises(
            consul.ACLPermissionDenied,
            c.kv.delete, 'private/foo', token=token)

        # clean up
        c.acl.destroy(token)
        acls = c.acl.list()
        assert set([x['ID'] for x in acls]) == \
            set(['anonymous', master_token])
