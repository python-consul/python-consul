from __future__ import absolute_import

from six import b
# noinspection PyUnresolvedReferences
from treq.client import HTTPClient as TreqHTTPClient
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.error import ConnectError
from twisted.internet.ssl import ClientContextFactory
from twisted.web._newclient import \
    ResponseNeverReceived, RequestTransmissionFailed
from twisted.web.client import Agent, HTTPConnectionPool

from consul import base
from consul.base import ConsulException

__all__ = ['Consul']


# noinspection PyClassHasNoInit
class InsecureContextFactory(ClientContextFactory):
    """
    This is an insecure context factory implementation. Note that this is not
    intended for production use. It is recommended either a treq/twisted
    provided factory be used or a custom factory for this purpose.

    https://twistedmatrix.com/documents/current/core/howto/ssl.html
    """

    def getContext(self, hostname, port):
        return ClientContextFactory.getContext(self)


class HTTPClient(base.HTTPClient):
    def __init__(self, contextFactory, *args, **kwargs):
        super(HTTPClient, self).__init__(*args, **kwargs)
        agent_kwargs = dict(
            reactor=reactor, pool=HTTPConnectionPool(reactor))
        if contextFactory is not None:
            # use the provided context factory
            agent_kwargs['contextFactory'] = contextFactory
        elif not self.verify:
            # if no context is provided and verify is set to false, use the
            # insecure context factory implementation
            agent_kwargs['contextFactory'] = InsecureContextFactory()

        self.client = TreqHTTPClient(Agent(**agent_kwargs))

    @staticmethod
    def response(code, headers, text):
        return base.Response(code, headers, text)

    @staticmethod
    def compat_string(value):
        """
        Provide a python2/3 compatible string representation of the value
        :type value:
        :rtype :
        """
        if isinstance(value, bytes):
            return value.decode(encoding='utf-8')
        return str(value)

    @inlineCallbacks
    def _get_resp(self, response):
        # Merge multiple header values as per RFC2616
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.2
        headers = dict([
            (self.compat_string(k), ','.join(map(self.compat_string, v)))
            for k, v in dict(response.headers.getAllRawHeaders()).items()
        ])
        body = yield response.text(encoding='utf-8')
        returnValue((response.code, headers, body))

    @inlineCallbacks
    def request(self, callback, method, url, **kwargs):
        if 'data' in kwargs and not isinstance(kwargs['data'], bytes):
            # python2/3 compatibility
            data = kwargs.pop('data')
            kwargs['data'] = data.encode(encoding='utf-8') \
                if hasattr(data, 'encode') else b(data)

        try:
            response = yield self.client.request(method, url, **kwargs)
            parsed = yield self._get_resp(response)
            returnValue(callback(self.response(*parsed)))
        except ConnectError as e:
            raise ConsulException(
                '{}: {}'.format(e.__class__.__name__, e.message))
        except ResponseNeverReceived:
            # this exception is raised if the connection to the server is lost
            # when yielding a response, this could be due to network issues or
            # server restarts
            raise ConsulException(
                'Server connection lost: {} {}'.format(method.upper(), url))
        except RequestTransmissionFailed:
            # this exception is expected if the reactor is stopped mid request
            raise ConsulException(
                'Request incomplete: {} {}'.format(method.upper(), url))

    @inlineCallbacks
    def get(self, callback, path, params=None):
        uri = self.uri(path, params)
        response = yield self.request(callback, 'get', uri, params=params)
        returnValue(response)

    @inlineCallbacks
    def put(self, callback, path, params=None, data=''):
        uri = self.uri(path, params)
        response = yield self.request(callback, 'put', uri, data=data)
        returnValue(response)

    @inlineCallbacks
    def post(self, callback, path, params=None, data=''):
        uri = self.uri(path, params)
        response = yield self.request(callback, 'post', uri, data=data)
        returnValue(response)

    @inlineCallbacks
    def delete(self, callback, path, params=None):
        uri = self.uri(path, params)
        response = yield self.request(callback, 'delete', uri, params=params)
        returnValue(response)


class Consul(base.Consul):
    @staticmethod
    def connect(host,
                port,
                scheme,
                verify=True,
                cert=None,
                contextFactory=None,
                **kwargs):
        return HTTPClient(
            contextFactory, host, port, scheme, verify=verify, cert=cert,
            **kwargs)
