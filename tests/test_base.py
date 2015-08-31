import collections

import consul.base


Request = collections.namedtuple(
    'Request', ['method', 'path', 'params', 'data'])


class HTTPClient(object):
    def __init__(self, host=None, port=None, scheme=None, verify=True):
        pass

    def get(self, callback, path, params=None):
        return Request('get', path, params, None)

    def put(self, callback, path, params=None, data=''):
        return Request('put', path, params, data)

    def delete(self, callback, path, params=None):
        return Request('delete', path, params, None)


class Consul(consul.base.Consul):
    def connect(self, host, port, scheme, verify=True):
        return HTTPClient(host, port, scheme, verify=verify)


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
