from six.moves import urllib

import requests

from consul import base


__all__ = ['Consul']


class HTTPClient(object):
    def __init__(self, host='127.0.0.1', port=8500, scheme='http'):
        self.host = host
        self.port = port
        self.scheme = scheme
        self.base_uri = '%s://%s:%s' % (self.scheme, self.host, self.port)

    def response(self, response):
        return base.Response(
            response.status_code, response.headers, response.text)

    def uri(self, path, params=None):
        uri = self.base_uri + path
        if not params:
            return uri
        return '%s?%s' % (uri, urllib.parse.urlencode(params))

    def get(self, callback, path, params=None):
        uri = self.uri(path, params)
        return callback(self.response(requests.get(uri)))

    def put(self, callback, path, params=None, data=''):
        uri = self.uri(path, params)
        return callback(self.response(requests.put(uri, data=data)))

    def delete(self, callback, path, params=None):
        uri = self.uri(path, params)
        return callback(self.response(requests.delete(uri, params=params)))


class Consul(base.Consul):
    def connect(self, host, port, scheme):
        return HTTPClient(host, port, scheme)
