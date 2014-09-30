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
        """
        The KV endpoint is used to expose a simple key/value store. This can be
        used to store service configurations or other meta data in a simple
        way.
        """
        def __init__(self, agent):
            self.agent = agent

        def get(self, key, index=None, recurse=False):
            """
            Returns a tuple of (*index*, *value[s]*)

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            The *value* returned is for the specified key, or if *recurse* is
            True a list of *values* for all keys with the given prefix is
            returned.

            Each *value* looks like this::

                {
                    "CreateIndex": 100,
                    "ModifyIndex": 200,
                    "LockIndex": 200,
                    "Key": "foo",
                    "Flags": 0,
                    "Value": "bar",
                    "Session": "adf4238a-882b-9ddc-4a9d-5b6758e4159e"
                }
            """
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
            """
            Sets *key* to the given *value*.

            The return value is simply either True or False. If False is
            returned, then the update has not taken place.
            """
            assert not key.startswith('/')

            def callback(response):
                return json.loads(response.body)

            return self.agent.http.put(callback, '/v1/kv/%s' % key, data=value)

    class Agent(object):
        """
        The Agent endpoints are used to interact with a local Consul agent.
        Usually, services and checks are registered with an agent, which then
        takes on the burden of registering with the Catalog and performing
        anti-entropy to recover from outages.
        """
        def __init__(self, agent):
            self.agent = agent
            self.service = Consul.Agent.Service(agent)

        def self(self):
            """
            Returns configuration of the local agent and member information.
            """
            return self.agent.http.get(
                lambda x: json.loads(x.body), '/v1/agent/self')

        def services(self):
            """
            Returns all the services that are registered with the local agent.
            These services were either provided through configuration files, or
            added dynamically using the HTTP API. It is important to note that
            the services known by the agent may be different than those
            reported by the Catalog. This is usually due to changes being made
            while there is no leader elected. The agent performs active
            anti-entropy, so in most situations everything will be in sync
            within a few seconds.
            """
            return self.agent.http.get(
                lambda x: json.loads(x.body), '/v1/agent/services')

        class Service(object):
            def __init__(self, agent):
                self.agent = agent

            def register(
                self, name, service_id=None, port=None,
                    tags=None, check=None, interval=None, ttl=None):
                """
                Add a new service to the local agent. There is more
                documentation on services
                `here <http://www.consul.io/docs/agent/services.html>`_.
                Services may also provide a health check. The agent is
                responsible for managing the status of the check and keeping
                the Catalog in sync.
                """

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
                """
                Used to remove a service from the local agent. The agent will
                take care of deregistering the service with the Catalog. If
                there is an associated check, that is also deregistered.
                """
                return self.agent.http.get(
                    lambda x: x.code == 200,
                    '/v1/agent/service/deregister/%s' % service_id)

    class Health(object):
        def __init__(self, agent):
            self.agent = agent
            self.check = Consul.Health.Check(agent)

        def service(self, service, index=None, passing=None):
            """
            Returns a tuple of (*index*, *nodes*)

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *nodes* are the nodes providing the given service.

            Calling with *passing* set to True will filter results to only
            those nodes whose checks are currently passing.
            """
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
                """
                Mark a local TTL check as passing.
                """
                return self.agent.http.get(
                    lambda x: x.code == 200,
                    '/v1/agent/check/pass/%s' % check_id)
