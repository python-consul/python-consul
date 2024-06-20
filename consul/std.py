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

    def get(self, callback, path, params=None, timeout=None):
        uri = self.uri(path, params)
        # TODO: Work out behaviour when timeout is 0 (i.e. disable timeout)
        timeout = timeout if timeout else self.timeout
        return callback(self.response(
            self.session.get(uri, verify=self.verify, cert=self.cert, timeout=timeout)))

    def put(self, callback, path, params=None, data='', timeout=None):
        uri = self.uri(path, params)
        # TODO: Work out behaviour when timeout is 0 (i.e. disable timeout)
        timeout = timeout if timeout else self.timeout
        return callback(self.response(
            self.session.put(uri, data=data, verify=self.verify,
                             cert=self.cert, timeout=timeout)))

    def delete(self, callback, path, params=None, timeout=None):
        uri = self.uri(path, params)
        # TODO: Work out behaviour when timeout is 0 (i.e. disable timeout)
        timeout = timeout if timeout else self.timeout
        return callback(self.response(
            self.session.delete(uri, verify=self.verify, cert=self.cert,
                                timeout=timeout)))

    def post(self, callback, path, params=None, data='', timeout=None):
        uri = self.uri(path, params)
        # TODO: Work out behaviour when timeout is 0 (i.e. disable timeout)
        timeout = timeout if timeout else self.timeout
        return callback(self.response(
            self.session.post(uri, data=data, verify=self.verify,
                              cert=self.cert, timeout=timeout)))


class Consul(base.Consul):
    def connect(self, host, port, scheme, verify=True, cert=None, timeout=None):
        return HTTPClient(host, port, scheme, verify, cert, timeout)
