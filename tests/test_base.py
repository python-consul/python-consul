import collections

import pytest

import consul.base


Request = collections.namedtuple(
    'Request', ['method', 'path', 'params', 'data'])


class HTTPClient(object):
    def __init__(self, host=None, port=None, scheme=None,
                 verify=True, cert=None):
        pass

    def get(self, callback, path, params=None):
        return Request('get', path, params, None)

    def put(self, callback, path, params=None, data=''):
        return Request('put', path, params, data)

    def delete(self, callback, path, params=None):
        return Request('delete', path, params, None)


class Consul(consul.base.Consul):
    def connect(self, host, port, scheme, verify=True, cert=None):
        return HTTPClient(host, port, scheme, verify=verify, cert=None)


def _should_support(c):
    return (
        # kv
        lambda **kw: c.kv.get('foo', **kw),
        # catalog
        c.catalog.nodes,
        c.catalog.services,
        lambda **kw: c.catalog.node('foo', **kw),
        lambda **kw: c.catalog.service('foo', **kw),
        # session
        c.session.list,
        lambda **kw: c.session.info('foo', **kw),
        lambda **kw: c.session.node('foo', **kw),
    )


class TestIndex(object):
    """
    Tests read requests that should support blocking on an index
    """
    def test_index(self):
        c = Consul()
        for r in _should_support(c):
            assert r().params == {}
            assert r(index='5').params == {'index': '5'}


class TestConsistency(object):
    """
    Tests read requests that should support consistency modes
    """
    def test_explict(self):
        c = Consul()
        for r in _should_support(c):
            assert r().params == {}
            assert r(consistency='default').params == {}
            assert r(consistency='consistent').params == {'consistent': '1'}
            assert r(consistency='stale').params == {'stale': '1'}

    def test_implicit(self):
        c = Consul(consistency='consistent')
        for r in _should_support(c):
            assert r().params == {'consistent': '1'}
            assert r(consistency='default').params == {}
            assert r(consistency='consistent').params == {'consistent': '1'}
            assert r(consistency='stale').params == {'stale': '1'}


class TestChecks(object):
    """
    Check constructor helpers return valid check configurations.
    """
    @pytest.mark.parametrize(
        'url, interval, timeout, deregister, want', [
            ('http://example.com', '10s', None, None, {
                'http': 'http://example.com',
                'interval': '10s',
            }),
            ('http://example.com', '10s', '1s', None, {
                'http': 'http://example.com',
                'interval': '10s',
                'timeout': '1s',
            }),
            ('http://example.com', '10s', None, '1m', {
                'http': 'http://example.com',
                'interval': '10s',
                'DeregisterCriticalServiceAfter': '1m',
            }),
            ('http://example.com', '10s', '1s', '1m', {
                'http': 'http://example.com',
                'interval': '10s',
                'timeout': '1s',
                'DeregisterCriticalServiceAfter': '1m',
            }),
        ])
    def test_http_check(self, url, interval, timeout, deregister, want):
        ch = consul.base.Check.http(url, interval, timeout=timeout,
                                    deregister=deregister)
        assert ch == want

    @pytest.mark.parametrize(
        'host, port, interval, timeout, deregister, want',
        [
            ('localhost', 1234, '10s', None, None, {
                'tcp': 'localhost:1234',
                'interval': '10s',
            }),
            ('localhost', 1234, '10s', '1s', None, {
                'tcp': 'localhost:1234',
                'interval': '10s',
                'timeout': '1s',
            }),
            ('localhost', 1234, '10s', None, '1m', {
                'tcp': 'localhost:1234',
                'interval': '10s',
                'DeregisterCriticalServiceAfter': '1m',
            }),
            ('localhost', 1234, '10s', '1s', '1m', {
                'tcp': 'localhost:1234',
                'interval': '10s',
                'timeout': '1s',
                'DeregisterCriticalServiceAfter': '1m',
            }),
        ])
    def test_tcp_check(self, host, port, interval, timeout, deregister, want):
        ch = consul.base.Check.tcp(host, port, interval, timeout=timeout,
                                   deregister=deregister)
        assert ch == want

    @pytest.mark.parametrize(
        'container_id, shell, script, interval, deregister, want',
        [
            ('wandering_bose', '/bin/sh', '/bin/true', '10s', None, {
                'docker_container_id': 'wandering_bose',
                'shell': '/bin/sh',
                'script': '/bin/true',
                'interval': '10s',
            }),
            ('wandering_bose', '/bin/sh', '/bin/true', '10s', '1m', {
                'docker_container_id': 'wandering_bose',
                'shell': '/bin/sh',
                'script': '/bin/true',
                'interval': '10s',
                'DeregisterCriticalServiceAfter': '1m',
            }),
        ])
    def test_docker_check(self, container_id, shell, script, interval,
                          deregister, want):
        ch = consul.base.Check.docker(container_id, shell, script, interval,
                                      deregister=deregister)
        assert ch == want

    def test_ttl_check(self):
        ch = consul.base.Check.ttl('1m')
        assert ch == {'ttl': '1m'}
