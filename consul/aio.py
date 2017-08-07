from __future__ import absolute_import
import sys
import asyncio
import warnings

import aiohttp
from consul import base


__all__ = ['Consul']
PY_341 = sys.version_info >= (3, 4, 1)


class HTTPClient(base.HTTPClient):
    """Asyncio adapter for python consul using aiohttp library"""

    def __init__(self, *args, loop=None, **kwargs):
        super(HTTPClient, self).__init__(*args, **kwargs)
        self._loop = loop or asyncio.get_event_loop()
        connector = aiohttp.TCPConnector(loop=self._loop,
                                         verify_ssl=self.verify)
        self._session = aiohttp.ClientSession(connector=connector)

    @asyncio.coroutine
    def _request(self, callback, method, uri, data=None):
        resp = yield from self._session.request(method, uri, data=data)
        body = yield from resp.text(encoding='utf-8')
        if resp.status == 599:
            raise base.Timeout
        r = base.Response(resp.status, resp.headers, body)
        return callback(r)

    # python prior 3.4.1 does not play nice with __del__ method
    if PY_341:  # pragma: no branch
        def __del__(self):
            if not self._session.closed:
                warnings.warn("Unclosed connector in aio.Consul.HTTPClient",
                              ResourceWarning)
                self.close()

    def get(self, callback, path, params=None):
        uri = self.uri(path, params)
        return self._request(callback, 'GET', uri)

    def put(self, callback, path, params=None, data=''):
        uri = self.uri(path, params)
        return self._request(callback, 'PUT', uri, data=data)

    def delete(self, callback, path, params=None):
        uri = self.uri(path, params)
        return self._request(callback, 'DELETE', uri)

    def post(self, callback, path, params=None, data=''):
        uri = self.uri(path, params)
        return self._request(callback, 'POST', uri, data=data)

    def close(self):
        self._session.close()


class Consul(base.Consul):

    def __init__(self, *args, loop=None, **kwargs):
        self._loop = loop or asyncio.get_event_loop()
        super().__init__(*args, **kwargs)

    def connect(self, host, port, scheme, verify=True, cert=None):
        return HTTPClient(host, port, scheme, loop=self._loop,
                          verify=verify, cert=None)

    def close(self):
        """Close all opened http connections"""
        self.http.close()
