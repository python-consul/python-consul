import collections
import base64
import json


class ACLDisabled(Exception):
    pass


class ACLPermissionDenied(Exception):
    pass


class Timeout(Exception):
    pass


Response = collections.namedtuple('Response', ['code', 'headers', 'body'])


class Consul(object):
    def __init__(self, host='127.0.0.1', port=8500):
        self.http = self.connect(host, port)
        self.kv = Consul.KV(self)
        self.agent = Consul.Agent(self)
        self.health = Consul.Health(self)
        self.acl = Consul.ACL(self)

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

        def put(self, key, value, cas=None, flags=None):
            """
            Sets *key* to the given *value*.

            The optional *cas* parameter is used to turn the PUT into a
            Check-And-Set operation. This is very useful as it allows clients
            to build more complex syncronization primitives on top. If the
            index is 0, then Consul will only put the key if it does not
            already exist. If the index is non-zero, then the key is only set
            if the index matches the ModifyIndex of that key.

            An optional *flags* can be set. This can be used to specify an
            unsigned value between 0 and 2^64-1.

            The return value is simply either True or False. If False is
            returned, then the update has not taken place.
            """
            assert not key.startswith('/')
            params = {}
            if cas is not None:
                params['cas'] = cas
            if flags is not None:
                params['flags'] = flags

            def callback(response):
                return json.loads(response.body)

            return self.agent.http.put(
                callback, '/v1/kv/%s' % key, params=params, data=value)

        def delete(self, key, recurse=None):
            """
            Deletes a single key or if *recurse* is True, all keys sharing a
            prefix.
            """
            assert not key.startswith('/')
            params = {}
            if recurse:
                params['recurse'] = '1'
            return self.agent.http.delete(
                lambda x: x.code == 200, '/v1/kv/%s' % key, params=params)

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

    class ACL(object):
        def __init__(self, agent):
            self.agent = agent

        def list(self, token=None):
            params = {}
            if token:
                params['token'] = token

            def callback(response):
                if response.code == 401:
                    raise ACLDisabled(response.body)
                if response.code == 403:
                    raise ACLPermissionDenied(response.body)
                return json.loads(response.body)

            return self.agent.http.get(callback, '/v1/acl/list', params=params)

        def info(self, acl_id, token=None):
            params = {}
            if token:
                params['token'] = token

            def callback(response):
                response = json.loads(response.body)
                if response:
                    return response[0]

            return self.agent.http.get(
                callback, '/v1/acl/info/%s' % acl_id, params=params)
