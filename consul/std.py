import requests

from consul import base


__all__ = ['Consul']


class HTTPClient(base.HTTPClient):
    def __init__(self, *args, **kwargs):
        super(HTTPClient, self).__init__(*args, **kwargs)
        self.session = requests.session()

    def response(self, response):
        response.encoding = 'utf-8'
        return base.Response(
            response.status_code, response.headers, response.text)

    def get(self, callback, path, params=None):
        uri = self.uri(path, params)
        return callback(self.response(
            self.session.get(uri, verify=self.verify, cert=self.cert, headers=self.headers)))

    def put(self, callback, path, params=None, data=''):
        uri = self.uri(path, params)
        return callback(self.response(
            self.session.put(uri, data=data, verify=self.verify,
                             cert=self.cert, headers=self.headers)))

    def delete(self, callback, path, params=None):
        uri = self.uri(path, params)
        return callback(self.response(
            self.session.delete(uri, verify=self.verify, cert=self.cert, headers=self.headers)))

    def post(self, callback, path, params=None, data=''):
        uri = self.uri(path, params)
        return callback(self.response(
            self.session.post(uri, data=data, verify=self.verify,
                              cert=self.cert, headers=self.headers)))


class Consul(base.Consul):
    def connect(self, host, port, scheme, verify=True, cert=None, token=None):
        headers = dict()
        if token is not None:
            headers['X-Consul-Token'] = token
        return HTTPClient(host, port, scheme, verify, cert, headers)
