import collections
import urllib
import types

import requests


Response = collections.namedtuple('Response', ['code', 'headers', 'body'])


class HTTPClient(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.base_uri = 'http://%s:%s' % (self.host, self.port)

    def response(self, response):
        return Response(response.status_code, response.headers, response.text)

    def uri(self, paths, params=None):
        uri = self.base_uri + '/'.join(paths)
        if not params:
            return uri
        return '%s?%s' % (uri, urllib.urlencode(params))

    def get(self, callback, uri, params=None, data=None):
        print uri
        return callback(self.response(requests.get(uri)))

    def put(self, callback, uri, params=None, data=None):
        print uri
        return callback(self.response(requests.put(uri, data=data)))


def prepare_params(values):
    ret = {}
    if values.get('index'):
        ret['index'] = values['index']
    if values.get('recurse'):
        ret['recurse'] = '1'
    return ret


def execute(http, method, path, name, args, local):
    if method == 'put':
        data = local[args[-1]]
        args = args[:-1]
    else:
        data = None

    uri = http.uri(
        [path, name] + [local[x] for x in args],
        params=prepare_params(local))

    return getattr(http, method)(lambda x: x, uri, data)


def command(method, *args, **kwargs):
    def make(http, path, name):
        # generate signature
        params = kwargs.pop('params', None)
        code = "def " + name + "("
        if args:
            code += ', '.join(args)
            if params: code += ', '
        if params:
            code += ', '.join(['%s=None' % x for x in params])
        code += '):'

        # body
        code += """
            return execute(http, method, path, name, args, locals())
        """

        # generate code
        ns = {
            'execute': execute,
            'http': http,
            'method': method,
            'path': path,
            'name': name,
            'args': args, }
        exec code in ns
        return ns[name]
    return make



commands = {
    'v1': {
        'kv': {
            'get': command('get', 'key', params=['index', 'recurse']),
            'put': command('put', 'key', 'value'),
        },
        'agent': {
            'self': command('get'),
            'service': {
                'register': command('get', 'name'),
            },
        },
        'health': lambda *a: None,
    }, }


class EndPoint(object):
    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return 'EndPoint("%s")' % self.path


def f(http, commands, path):
    endpoint = EndPoint(path)
    for key, command in commands.iteritems():
        if isinstance(command, dict):
            setattr(endpoint, key, f(http, command, path+'/'+key))
        else:
            setattr(endpoint, key, command(http, path, key))
    return endpoint


def main():

    import inspect

    http = HTTPClient('localhost', 8500)

    api = f(http, commands['v1'], '/v1')

    print api.agent.service.register
    print inspect.getargspec(api.agent.service.register)
    print api.agent.service.register('foo')

    return
    print api.kv.put('foo', 'bar')
    print api.kv.get('foo')


main()
