import urllib3

from consul import base


__all__ = ['Consul']
JSON_HEADER = {'Content-Type': 'application/json'}


class HTTPClient(base.HTTPClient):
    def __init__(self, *args, **kwargs):
        super(HTTPClient, self).__init__(*args, **kwargs)
        cert_file = kwargs.get('cert', None)
        cert_reqs = 'CERT_REQUIRED' if kwargs.get('verify', False) else None
        self.session = urllib3.PoolManager(cert_file=cert_file, cert_reqs=cert_reqs)

    def response(self, response):
        return base.Response(
            response.status, response.headers, response.data.decode('utf-8'))

    def get(self, callback, path, params=None):
        uri = self.uri(path, params)
        return callback(self.response(
            self.session.request('GET', uri)))

    def put(self, callback, path, params=None, data=''):
        uri = self.uri(path, params)
        return callback(self.response(
            self.session.request('PUT', uri, body=data, headers=JSON_HEADER)))

    def delete(self, callback, path, params=None):
        uri = self.uri(path, params)
        return callback(self.response(
            self.session.request('DELETE', uri)))

    def post(self, callback, path, params=None, data=''):
        uri = self.uri(path, params)
        return callback(self.response(
            self.session.request('POST', uri, body=data, headers=JSON_HEADER)))


class Consul(base.Consul):
    def connect(self, host, port, scheme, verify=True, cert=None):
        return HTTPClient(host, port, scheme, verify, cert)
