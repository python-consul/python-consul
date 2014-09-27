import collections
import base64
import json


class Timeout(Exception):
    pass


Response = collections.namedtuple('Response', ['code', 'headers', 'body'])


class Consul(object):
    def __init__(self, host='127.0.0.1', port=8500):
        self.http = self.connect(host, port)
        self.kv = Consul.KV(self)
        self.agent = Consul.Agent(self)
        self.health = Consul.Health(self)

    class KV(object):
        def __init__(self, agent):
            self.agent = agent

        def get(self, key, index=None, recurse=False):
            assert not key.startswith('/')
            params = {}
            if index:
                params['index'] = index
            if recurse:
                params['recurse'] = '1'

            def callback(response):
                if response.code == 404:
                    data = None
                else:
                    data = json.loads(response.body)
                    for item in data:
                        item['Value'] = base64.b64decode(item['Value'])
                    if not recurse:
                        data = data[0]
                return response.headers['X-Consul-Index'], data

            return self.agent.http.get(
                callback, '/v1/kv/%s' % key, params=params)

        def put(self, key, value):
            assert not key.startswith('/')

            def callback(response):
                return json.loads(response.body)

            return self.agent.http.put(callback, '/v1/kv/%s' % key, data=value)

    class Agent(object):
        def __init__(self, agent):
            self.agent = agent
            self.service = Consul.Agent.Service(agent)

        def self(self):
            return self.agent.http.get(
                lambda x: json.loads(x.body), '/v1/agent/self')

        def services(self):
            return self.agent.http.get(
                lambda x: json.loads(x.body), '/v1/agent/services')

        class Service(object):
            def __init__(self, agent):
                self.agent = agent

            def register(
                self, name, service_id=None, port=None,
                    tags=None, check=None, interval=None, ttl=None):

                payload = {
                    'id': service_id,
                    'name': name,
                    'port': port,
                    'tags': tags,
                    'check': {
                        'script': check,
                        'interval': interval,
                        'ttl': ttl, }}

                return self.agent.http.put(
                    lambda x: x.code == 200,
                    '/v1/agent/service/register',
                    data=json.dumps(payload))

            def deregister(self, service_id):
                return self.agent.http.get(
                    lambda x: x.code == 200,
                    '/v1/agent/service/deregister/%s' % service_id)

    class Health(object):
        def __init__(self, agent):
            self.agent = agent
            self.check = Consul.Health.Check(agent)

        def service(self, service, index=None, passing=None):
            params = {}
            if index:
                params['index'] = index
            if passing:
                params['passing'] = '1'

            def callback(response):
                data = json.loads(response.body)
                return response.headers['X-Consul-Index'], data

            return self.agent.http.get(
                callback,
                '/v1/health/service/%s' % service, params=params)

        class Check(object):
            def __init__(self, agent):
                self.agent = agent

            def ttl_pass(self, check_id):
                return self.agent.http.get(
                    lambda x: x.code == 200,
                    '/v1/agent/check/pass/%s' % check_id)
