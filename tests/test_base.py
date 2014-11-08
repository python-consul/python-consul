import collections

import consul.base


Request = collections.namedtuple(
    'Request', ['method', 'path', 'params', 'data'])


class HTTPClient(object):
    def __init__(self, host=None, port=None):
        pass

    def get(self, callback, path, params=None):
        return Request('get', path, params, None)

    def put(self, callback, path, params=None, data=''):
        return Request('put', path, params, data)

    def delete(self, callback, path, params=None):
        return Request('delete', path, params, None)


class Consul(consul.base.Consul):
    def connect(self, host, port):
        return HTTPClient(host, port)


class TestConsistency(object):
    """
    Tests read requests that should support consistency modes
    """
    def _should_support(self, c):
        return (
            c.catalog.nodes,
            c.catalog.services,
            lambda **kw: c.catalog.node('foo', **kw),
            lambda **kw: c.catalog.service('foo', **kw),)

    def test_explict(self):
        c = Consul()
        for r in self._should_support(c):
            assert r().params == {}
            assert r(consistency='default').params == {}
            assert r(consistency='consistent').params == {'consistent': '1'}
            assert r(consistency='stale').params == {'stale': '1'}

    def test_implicit(self):
        c = Consul(consistency='consistent')
        for r in self._should_support(c):
            assert r().params == {'consistent': '1'}
            assert r(consistency='default').params == {}
            assert r(consistency='consistent').params == {'consistent': '1'}
            assert r(consistency='stale').params == {'stale': '1'}
