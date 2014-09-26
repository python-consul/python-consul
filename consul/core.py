import collections
import urllib2
import urllib


__version__ = '0.1'


__all__ = ['__version__', 'connect']


def command(last, method, *args, **kwargs):
    def make(http, path, name):
        if last is not None:
            path = path + '/' + last

        # generate signature
        params = kwargs.pop('params', None)
        code = "def " + name + "("
        if args:
            code += ', '.join(args)
            if params:
                code += ', '
        if params:
            code += ', '.join(['%s=None' % x for x in params])
        code += '):'

        # body
        code += """
            return execute(http, method, path, args, locals())
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
            'get': command(None, 'get', 'key', params=['index', 'recurse']),
            'put': command(None, 'put', 'key', 'value'),
        },
        'agent': {
            'self': command('self', 'get'),
            'service': {
                'register': command('register', 'get', 'name'),
            },
        },
        'health': lambda *a: None,
    }, }


Response = collections.namedtuple('Response', ['code', 'headers', 'body'])


class HTTPClient(object):
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.base_uri = 'http://%s:%s' % (self.host, self.port)

    def response(self, fh):
        ret = Response(fh.getcode(), fh.info().dict, fh.read())
        fh.close()
        return ret

    def uri(self, paths, params=None):
        uri = self.base_uri + '/'.join(paths)
        if not params:
            return uri
        return '%s?%s' % (uri, urllib.urlencode(params))

    def get(self, callback, uri, params=None, data=None):
        print
        print uri
        response = self.response(urllib.urlopen(uri))
        return callback(response)

    def put(self, callback, uri, params=None, data=None):
        print
        print uri
        opener = urllib2.build_opener(urllib2.HTTPHandler)
        request = urllib2.Request(uri, data=data)
        # request.add_header('Content-Type', 'your/contenttype')
        request.get_method = lambda: 'PUT'
        try:
            response = opener.open(request)
        except urllib2.HTTPError, response:
            pass
        response = self.response(response)
        return callback(response)


def prepare_params(values):
    ret = {}
    if values.get('index'):
        ret['index'] = values['index']
    if values.get('recurse'):
        ret['recurse'] = '1'
    return ret


def execute(http, method, path, args, local):
    if method == 'put':
        data = local[args[-1]]
        args = args[:-1]
    else:
        data = None

    uri = http.uri(
        [path] + [local[x] for x in args], params=prepare_params(local))

    return getattr(http, method)(lambda x: x, uri, data)


class EndPoint(object):
    def __init__(self, path):
        self.path = path

    def __repr__(self):
        return 'EndPoint("%s")' % self.path


def build(http, commands, path):
    endpoint = EndPoint(path)
    for key, command in commands.iteritems():
        if isinstance(command, dict):
            setattr(endpoint, key, build(http, command, path+'/'+key))
        else:
            setattr(endpoint, key, command(http, path, key))
    return endpoint


def connect(host='127.0.0.1', port=8500):
    http = HTTPClient(host, port)
    return build(http, commands['v1'], '/v1')
