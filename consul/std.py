import requests

from six.moves import urllib

from consul import base


__all__ = ['Consul']


class HTTPClient(base.HTTPClient):
    def __init__(self, *args, **kwargs):
        super(HTTPClient, self).__init__(*args, **kwargs)
        if 'unix://' in self.base_uri:
            pr = urllib.parse.urlparse(self.base_uri)
            netloc = urllib.parse.quote_plus(pr.path)
            self.base_uri = 'http+unix://{0}'.format(netloc)
            try:
                import requests_unixsocket
                self.session = requests_unixsocket.Session()
            except ImportError:
                raise base.ConsulException('To use a unix socket to connect to'
                                           ' Consul you need to install the'
                                           ' "requests_unixsocket" package.')
        else:
            self.session = requests.session()

    def response(self, response):
        response.encoding = 'utf-8'
        return base.Response(
            response.status_code, response.headers, response.text)

    def get(self, callback, path, params=None):
        uri = self.uri(path, params)
        return callback(self.response(
            self.session.get(uri, verify=self.verify, cert=self.cert)))

    def put(self, callback, path, params=None, data=''):
        uri = self.uri(path, params)
        return callback(self.response(
            self.session.put(uri, data=data, verify=self.verify,
                             cert=self.cert)))

    def delete(self, callback, path, params=None):
        uri = self.uri(path, params)
        return callback(self.response(
            self.session.delete(uri, verify=self.verify, cert=self.cert)))

    def post(self, callback, path, params=None, data=''):
        uri = self.uri(path, params)
        return callback(self.response(
            self.session.post(uri, data=data, verify=self.verify,
                              cert=self.cert)))


class Consul(base.Consul):
    def connect(self, base_uri, verify=True, cert=None, auth=None):
        return HTTPClient(base_uri, verify=verify, cert=cert, auth=auth)
