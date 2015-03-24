"""A twisted integration for consul."""
from __future__ import absolute_import
from six.moves import urllib
from consul import base
from twisted.internet.error import ConnectError
from twisted.python import log

import treq


__all__ = ['Consul']


class HTTPClient(object):

    """A HTTPClient based off treq for twisted."""

    def __init__(self, host="127.0.0.1", port=8500, scheme="http"):
        self.host = host
        self.port = port
        self.scheme = scheme
        self.base_uri = '%s://%s:%s' % (self.scheme, self.host, self.port)
        self.client = treq

    def uri(self, path, params=None):
        uri = self.base_uri + path
        if not params:
            return uri
        return '%s?%s' % (uri, urllib.parse.urlencode(params))

    def wrap_response(self, response, content):

        class HeaderWrapper(object):
            headers = response.headers

            def __getitem__(self, key):
                return self.headers.getRawHeaders(key)[0]
        return base.Response(
            response.code, HeaderWrapper(), content)

    def _request(self, callback, method, **kwargs):
        d = method(**kwargs)
        d.addCallback(self._handle_response)
        d.addErrback(self.error)
        d.addCallback(callback)
        return d

    def _handle_response(self, response):
        d = response.text(encoding="utf8")
        d.addCallback(
            lambda _cont, _resp: self.wrap_response(_resp, _cont),
            response
        )
        return d

    def error(self, error):
        print error
        r = error.trap(ConnectError)
        if r is ConnectError:
            log.err("Is the Consul server running and accessible?")
            return error

    def get(self, callback, path, params=None):
        uri = self.uri(path, params)
        return self._request(callback, self.client.get, url=uri)

    def put(self, callback, path, params=None, data=''):
        uri = self.uri(path, params)
        return self._request(callback, self.client.put, url=uri, data=data)

    def delete(self, callback, path, params=None):
        uri = self.uri(path, params)
        return self._request(callback, self.client.delete, url=uri)


class Consul(base.Consul):

    """Subclass of consul to use twisted http client."""

    def connect(self, host, port, scheme):
        """Return a treq based http client."""
        return HTTPClient(host, port, scheme)
