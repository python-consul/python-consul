from __future__ import absolute_import

from ssl import CERT_REQUIRED, CERT_OPTIONAL, CERT_NONE

# noinspection PyUnresolvedReferences
from six.moves import urllib
from treq.client import HTTPClient as TreqHTTPClient
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue, log
from twisted.internet.error import ConnectError
from twisted.internet.ssl import ClientContextFactory
from twisted.web.client import Agent, HTTPConnectionPool, SSL

from consul import base
from consul.base import ConsulException

__all__ = ['Consul']

try:
    from ssl import _DEFAULT_CIPHERS as DEFAULT_CIPHERS
except ImportError:
    DEFAULT_CIPHERS = (
        'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:'
        'ECDH+HIGH:DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:'
        'RSA+3DES:!aNULL:!eNULL:!MD5'
    )


class SSLSpec(object):
    SSLv2 = 'SSLv2'
    SSLv23 = 'SSLv23'
    SSLv3 = 'SSLv3'
    TLSv1 = 'TLSv1'
    TLSv1_1 = 'TLSv1_1'
    TLSv1_2 = 'TLSv1_2'

    SSL_VERSIONS = {SSLv2, SSLv23, SSLv3, TLSv1, TLSv1_1, TLSv1_2}

    OP_CIPHER_SERVER_PREFERENCE = 'OP_CIPHER_SERVER_PREFERENCE'
    OP_NO_COMPRESSION = 'OP_NO_COMPRESSION'
    OP_NO_SSLv2 = 'OP_NO_SSLv2'
    OP_NO_SSLv3 = 'OP_NO_SSLv3'
    OP_NO_TLSv1 = 'OP_NO_TLSv1'
    OP_NO_TLSv1_1 = 'OP_NO_TLSv1_1'
    OP_NO_TLSv1_2 = 'OP_NO_TLSv1_2'
    OP_SINGLE_DH_USE = 'OP_SINGLE_DH_USE'
    OP_SINGLE_ECDH_USE = 'OP_SINGLE_ECDH_USE'

    SSL_OPTIONS = {
        OP_CIPHER_SERVER_PREFERENCE, OP_NO_COMPRESSION, OP_NO_SSLv2,
        OP_NO_SSLv3, OP_NO_TLSv1, OP_NO_TLSv1_1, OP_NO_TLSv1_2,
        OP_SINGLE_DH_USE, OP_SINGLE_ECDH_USE
    }

    DEFAULT_SSL_OPTIONS = [
        OP_NO_SSLv2,
        OP_NO_SSLv3,
        OP_NO_COMPRESSION,
        OP_CIPHER_SERVER_PREFERENCE,
        OP_SINGLE_DH_USE,
        OP_SINGLE_ECDH_USE
    ]

    DEFAULT_CIPHERS = DEFAULT_CIPHERS

    CERT_REQUIRED = CERT_REQUIRED
    CERT_OPTIONAL = CERT_OPTIONAL
    CERT_NONE = CERT_NONE

    CERT_OPTIONS = {CERT_REQUIRED, CERT_OPTIONAL, CERT_NONE}


class AsyncClientSSLContextFactory(ClientContextFactory):
    __SSLVersions = set([x for x in dir(SSL) if x.endswith('_METHOD')])
    validSSLVersionStrings = set([x.rsplit('_')[0] for x in __SSLVersions])
    validSSLVersionInt = set([getattr(SSL, x) for x in __SSLVersions])
    validSSLOptions = set([x for x in dir(SSL) if x.startswith('OP_')])

    _ssl_to_openssl_verify_mapping = {
        SSLSpec.CERT_NONE: SSL.VERIFY_NONE,
        SSLSpec.CERT_OPTIONAL: SSL.VERIFY_PEER,
        SSLSpec.CERT_REQUIRED:
            SSL.VERIFY_PEER + SSL.VERIFY_FAIL_IF_NO_PEER_CERT,
    }

    def __init__(self, method=SSLSpec.SSLv23, verify=SSLSpec.CERT_REQUIRED,
                 options=None, ciphers=None, certFile=None, keyFile=None,
                 keyFilePassword=None, caFile=None, caPath=None):
        self.method = self._parseSSLMethod(method)
        self.options = self._parseSSLOptions(options)
        self.verify = verify
        self.ciphers = ciphers
        self.certFile = certFile
        self.keyFile = keyFile
        self.keyFilePassword = keyFilePassword
        self.caFile = caFile
        self.caPath = caPath

    def _parseSSLMethod(self, method):
        if isinstance(method, int):
            if method in self.validSSLVersionInt:
                return method
            else:
                raise ValueError(
                    'Invalid sslVersion {}, Valid values for sslVersion are {}'
                    .format(method, self.validSSLVersionStrings)
                )
        else:
            try:
                return getattr(SSL, "{}_METHOD".format(method))
            except AttributeError:
                raise ValueError(
                    'Invalid sslVersion (method) "{}". Valid versions are {}'
                    .format(method, self.validSSLVersionStrings)
                )

    def _parseSSLOptions(self, options):
        result = []
        if options is not None:
            for option in options:
                try:
                    result.append(getattr(SSL, option))
                except AttributeError:
                    log.debug(
                        'Invalid SSL option for this system: "{}", ignoring...'
                        .format(option)
                    )
        return result

    @staticmethod
    def _verifyCallback(cnx, x509, err_no, err_depth, return_code):
        return err_no == 0

    def _getKeyPassword(self):
        return self.keyFilePassword

    def getContext(self):
        """
        :return: an OpenSSL context used by Twisted
        :rtype: OpenSSL.SSL.Context
        """
        try:
            ctx = self._contextFactory(self.method)
        except AttributeError:
            raise ValueError(
                'Invalid sslVersion (method). Valid versions are {}'.format(
                    self.validSSLVersionStrings)
            )
        for op in self.options:
            ctx.set_options(op)
        if self.caFile is not None or self.caPath is not None:
            ctx.load_verify_locations(self.caFile, self.caPath)
        if self.ciphers is not None:
            ctx.set_cipher_list(self.ciphers)
        if self.certFile is not None:
            self.keyFile = self.keyFile \
                if self.keyFile is not None else self.certFile
            ctx.use_certificate_file(self.certFile)
        if self.keyFile is not None:
            ctx.use_privatekey_file(self.keyFile)
        if self.keyFilePassword is not None:
            ctx.set_passwd_cb(self._getKeyPassword)
        ctx.set_verify(self._ssl_to_openssl_verify_mapping[self.verify],
                       self._verifyCallback)
        return ctx


class HTTPClient(object):
    def __init__(self, host='127.0.0.1', port=8500, scheme='http',
                 verify=True):
        self.host = host
        self.port = port
        self.scheme = scheme
        self.base_uri = '%s://%s:%s' % (self.scheme, self.host, self.port)
        self.verify = SSLSpec.CERT_NONE \
            if not verify else SSLSpec.CERT_REQUIRED
        agent = Agent(reactor=reactor, pool=HTTPConnectionPool(reactor),
                      contextFactory=AsyncClientSSLContextFactory(
                          verify=self.verify))
        self.client = TreqHTTPClient(agent)

    def uri(self, path, params=None):
        uri = self.base_uri + path
        if not params:
            return uri
        return '%s?%s' % (uri, urllib.parse.urlencode(params))

    def response(self, code, headers, text):
        return base.Response(code, headers, text)

    @inlineCallbacks
    def _get_resp(self, response):
        # Merge multiple header values as per RFC2616
        # http://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.2
        headers = {
            k: ','.join(v)
            for k, v in dict(response.headers.getAllRawHeaders()).items()
        }
        body = yield response.text(encoding='utf-8')
        returnValue((response.code, headers, body))

    @inlineCallbacks
    def request(self, callback, method, url, **kwargs):
        try:
            response = yield self.client.request(method, url, **kwargs)
            parsed = yield self._get_resp(response)
            returnValue(callback(self.response(*parsed)))
        except ConnectError as e:
            raise ConsulException(
                '{}: {}'.format(e.__class__.__name__, e.message))

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
    def delete(self, callback, path, params=None):
        uri = self.uri(path, params)
        response = yield self.request(callback, 'delete', uri, params=params)
        returnValue(response)


class Consul(base.Consul):
    def connect(self, host, port, scheme, verify=True):
        return HTTPClient(host, port, scheme, verify=verify)
