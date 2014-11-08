import collections
import base64
import json


class ConsulException(Exception):
    pass


class ACLDisabled(ConsulException):
    pass


class ACLPermissionDenied(ConsulException):
    pass


class Timeout(ConsulException):
    pass


Response = collections.namedtuple('Response', ['code', 'headers', 'body'])


def callback(callback=None, is_200=False, is_indexed=False):
    def cb(response):
        if response.code == 500:
            raise ConsulException(response.body)
        if is_200:
            return response.code == 200
        if is_indexed:
            return (
                response.headers['X-Consul-Index'], json.loads(response.body))
        if callback:
            return callback(response)
        return response
    return cb


class Consul(object):
    def __init__(
            self,
            host='127.0.0.1',
            port=8500,
            token=None,
            consistency='default'):
        """
        *token* is an optional `ACL token`_. If supplied it will be used by
        default for all requests made with this client session. It's still
        possible to override this token by passing a token explicitly for a
        request.

        *consistency* sets the consistency mode to use by default for all reads
        that support the consistency option. It's still possible to override
        this by passing explicitly for a given request. *consistency* can be
        either 'default', 'consistent' or 'stale'.
        """

        # TODO: Session, Event, Status

        self.http = self.connect(host, port)
        self.token = token
        assert consistency in ('default', 'consistent', 'stale')
        self.consistency = consistency

        self.kv = Consul.KV(self)
        self.agent = Consul.Agent(self)
        self.catalog = Consul.Catalog(self)
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

        def get(self, key, index=None, recurse=False, token=None):
            """
            Returns a tuple of (*index*, *value[s]*)

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *token* is an optional `ACL token`_ to apply to this request.

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
            # TODO: supports consistency modes
            assert not key.startswith('/')
            params = {}
            if index:
                params['index'] = index
            if recurse:
                params['recurse'] = '1'
            token = token or self.agent.token
            if token:
                params['token'] = token

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

        def put(self, key, value, cas=None, flags=None, token=None):
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

            *token* is an optional `ACL token`_ to apply to this request. If
            the token's policy is not allowed to write to this key an
            *ACLPermissionDenied* exception will be raised.

            The return value is simply either True or False. If False is
            returned, then the update has not taken place.
            """
            assert not key.startswith('/')
            params = {}
            if cas is not None:
                params['cas'] = cas
            if flags is not None:
                params['flags'] = flags
            token = token or self.agent.token
            if token:
                params['token'] = token

            def callback(response):
                if response.code == 403:
                    raise ACLPermissionDenied(response.body)
                return json.loads(response.body)

            return self.agent.http.put(
                callback, '/v1/kv/%s' % key, params=params, data=value)

        def delete(self, key, recurse=None, token=None):
            """
            Deletes a single key or if *recurse* is True, all keys sharing a
            prefix.

            *token* is an optional `ACL token`_ to apply to this request. If
            the token's policy is not allowed to delete to this key an
            *ACLPermissionDenied* exception will be raised.
            """
            assert not key.startswith('/')

            params = {}
            if recurse:
                params['recurse'] = '1'
            token = token or self.agent.token
            if token:
                params['token'] = token

            def callback(response):
                if response.code == 403:
                    raise ACLPermissionDenied(response.body)
                return response.code == 200

            return self.agent.http.delete(
                callback, '/v1/kv/%s' % key, params=params)

    class Agent(object):
        """
        The Agent endpoints are used to interact with a local Consul agent.
        Usually, services and checks are registered with an agent, which then
        takes on the burden of registering with the Catalog and performing
        anti-entropy to recover from outages.
        """
        # TODO: checks, members, join, force-leave
        # TODO: Check. register, deregister, pass (move), warn, fail
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
                    tags=None, script=None, interval=None, ttl=None):
                """
                Add a new service to the local agent. There is more
                documentation on services
                `here <http://www.consul.io/docs/agent/services.html>`_.

                *name* is the name of the service.

                If the optional *service_id* is not provided it is set to
                *name*. You cannot have duplicate *service_id* entries per
                agent, so it may be necessary to provide one.

                An optional health check can be created for this service. The
                health check is only one of *script* and *interval* OR *ttl*.
                """
                payload = {'name': name}
                if service_id:
                    payload['id'] = service_id
                if port:
                    payload['port'] = port
                if tags:
                    payload['tags'] = tags
                if script:
                    assert interval and not ttl
                    payload['check'] = {'script': script, 'interval': interval}
                if ttl:
                    assert not (interval or script)
                    payload['check'] = {'ttl': ttl}

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

    class Catalog(object):
        def __init__(self, agent):
            self.agent = agent

        def register(self, node, address, dc=None, service=None, check=None):
            """
            A low level mechanism for directly registering or updating entries
            in the catalog. It is usually recommended to use
            agent.service.register and agent.check.register, as they are
            simpler and perform anti-entropy.

            *node* is the name of the node to register.

            *address* is the ip of the node.

            *dc* is the datacenter of the node and defaults to this agents
            datacenter.

            *service* is an optional service to register. if supplied this is a
            dict::

                {
                    "Service": "redis",
                    "ID": "redis1",
                    "Tags": [
                        "master",
                        "v1"
                    ],
                    "Port": 8000
                }

            where

                *Service* is required and is the name of the service

                *ID* is optional, and will be set to *Service* if not provided.
                Note *ID* must be unique for the given *node*.

                *Tags* and *Port* are optional.

            *check* is an optional check to register. if supplied this is a
            dict::

                {
                    "Node": "foobar",
                    "CheckID": "service:redis1",
                    "Name": "Redis health check",
                    "Notes": "Script based health check",
                    "Status": "passing",
                    "ServiceID": "redis1"
                }

            This manipulates the health check entry, but does not setup a
            script or TTL to actually update the status. The full documentation
            is `here <https://consul.io/docs/agent/http.html#catalog>`_.

            Returns *True* on success.
            """
            data = {'node': node, 'address': address}
            if dc:
                data['datacenter'] = dc
            if service:
                data['service'] = service
            if check:
                data['check'] = check
            return self.agent.http.put(
                callback(is_200=True),
                '/v1/catalog/register', data=json.dumps(data))

        def deregister(self, node, dc=None, service_id=None, check_id=None):
            """
            A low level mechanism for directly removing entries in the catalog.
            It is usually recommended to use the agent APIs, as they are
            simpler and perform anti-entropy.

            *node* and *dc* specify which node on which datacenter to remove.
            If *service_id* and *check_id* are not provided, all associated
            services and checks are deleted. Otherwise only one of *service_id*
            and *check_id* should be provided and only that service or check
            will be removed.

            Returns *True* on success.
            """
            assert not (service_id and check_id)
            data = {'node': node}
            if dc:
                data['datacenter'] = dc
            if service_id:
                data['serviceid'] = service_id
            if check_id:
                data['checkid'] = check_id
            return self.agent.http.put(
                callback(is_200=True),
                '/v1/catalog/deregister', data=json.dumps(data))

        def datacenters(self):
            """
            Returns all the datacenters that are known by the Consul server.
            """
            return self.agent.http.get(
                lambda x: json.loads(x.body), '/v1/catalog/datacenters')

        def nodes(self, dc=None, index=None, consistency=None):
            """
            Returns a tuple of (*index*, *nodes*) of all nodes known
            about in the *dc* datacenter. *dc* defaults to the current
            datacenter of this agent.

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *consistency* can be either 'default', 'consistent' or 'stale'. if
            not specified *consistency* will the consistency level this client
            was configured with.

            The response looks like this::

                (index, [
                    {
                        "Node": "baz",
                        "Address": "10.1.10.11"
                    },
                    {
                        "Node": "foobar",
                        "Address": "10.1.10.12"
                    }
                ])
            """
            params = {}
            if dc:
                params['dc'] = dc
            return self.agent.http.get(
                callback(is_indexed=True), '/v1/catalog/nodes', params=params)

        def services(self, dc=None, index=None, consistency=None):
            """
            Returns a tuple of (*index*, *services*) of all services known
            about in the *dc* datacenter. *dc* defaults to the current
            datacenter of this agent.

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *consistency* can be either 'default', 'consistent' or 'stale'. if
            not specified *consistency* will the consistency level this client
            was configured with.

            The response looks like this::

                (index, {
                    "consul": [],
                    "redis": [],
                    "postgresql": [
                        "master",
                        "slave"
                    ]
                })

            The main keys are the service names and the list provides all the
            known tags for a given service.
            """
            params = {}
            if dc:
                params['dc'] = dc
            return self.agent.http.get(
                callback(is_indexed=True),
                '/v1/catalog/services', params=params)

        def node(self, node, dc=None, index=None, consistency=None):
            """
            Returns a tuple of (*index*, *services*) of all services provided
            by *node*.

            *dc* is the datacenter of the node and defaults to this agents
            datacenter.

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *consistency* can be either 'default', 'consistent' or 'stale'. if
            not specified *consistency* will the consistency level this client
            was configured with.

            The response looks like this::

                (index, {
                    "Node": {
                        "Node": "foobar",
                        "Address": "10.1.10.12"
                    },
                    "Services": {
                        "consul": {
                            "ID": "consul",
                            "Service": "consul",
                            "Tags": null,
                            "Port": 8300
                        },
                        "redis": {
                            "ID": "redis",
                            "Service": "redis",
                            "Tags": [
                                "v1"
                            ],
                            "Port": 8000
                        }
                    }
                })
            """
            params = {}
            if dc:
                params['dc'] = dc
            return self.agent.http.get(
                callback(is_indexed=True),
                '/v1/catalog/node/%s' % node, params=params)

        def service(
                self,
                service,
                dc=None,
                tag=None,
                index=None,
                consistency=None):
            """
            Returns a tuple of (*index*, *nodes*) of the nodes providing
            *service* in the *dc* datacenter. *dc* defaults to the current
            datacenter of this agent.

            If *tag* is provided, the list of nodes returned will be filtered
            by that tag.

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *consistency* can be either 'default', 'consistent' or 'stale'. if
            not specified *consistency* will the consistency level this client
            was configured with.

            The response looks like this::

                (index, [
                    {
                        "Node": "foobar",
                        "Address": "10.1.10.12",
                        "ServiceID": "redis",
                        "ServiceName": "redis",
                        "ServiceTags": null,
                        "ServicePort": 8000
                    }
                ])
            """
            params = {}
            if dc:
                params['dc'] = dc
            if tag:
                params['tag'] = tag
            return self.agent.http.get(
                callback(is_indexed=True),
                '/v1/catalog/service/%s' % service, params=params)

    class Health(object):
        # TODO: All of the health endpoints support blocking queries and all
        # consistency modes
        # TODO: Check ttl_pass belongs under Agent
        # TODO: still need to add node, checks and state endpoints
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
            """
            Lists all the active ACL tokens. This is a privileged endpoint, and
            requires a management token. *token* will override this client's
            default token.  An *ACLPermissionDenied* exception will be raised
            if a management token is not used.
            """
            params = {}
            token = token or self.agent.token
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
            """
            Returns the token information for *acl_id*.
            """
            params = {}
            token = token or self.agent.token
            if token:
                params['token'] = token

            def callback(response):
                if response.code == 401:
                    raise ACLDisabled(response.body)
                response = json.loads(response.body)
                if response:
                    return response[0]

            return self.agent.http.get(
                callback, '/v1/acl/info/%s' % acl_id, params=params)

        def create(self, name=None, type='client', rules=None, token=None):
            """
            Creates a new ACL token. This is a privileged endpoint, and
            requires a management token. *token* will override this client's
            default token.  An *ACLPermissionDenied* exception will be raised
            if a management token is not used.

            *name* is an optional name for this token.

            *type* is either 'management' or 'client'. A management token is
            effectively like a root user, and has the ability to perform any
            action including creating, modifying, and deleting ACLs. A client
            token can only perform actions as permitted by *rules*.

            *rules* is an optional `HCL`_ string for this `ACL Token`_ Rule
            Specification.

            Rules look like this::

                # Default all keys to read-only
                key "" {
                  policy = "read"
                }
                key "foo/" {
                  policy = "write"
                }
                key "foo/private/" {
                  # Deny access to the private dir
                  policy = "deny"
                }

            Returns the string *acl_id* for the new token.
            """
            params = {}
            token = token or self.agent.token
            if token:
                params['token'] = token

            payload = {}
            if name:
                payload['Name'] = name
            if type:
                assert type == 'client' or type == 'management'
                payload['Type'] = type
            if rules:
                assert isinstance(rules, str), \
                    'Only HCL encoded strings supported for the moment'
                payload['Rules'] = rules

            if payload:
                data = json.dumps(payload)
            else:
                data = ''

            def callback(response):
                if response.code == 401:
                    raise ACLDisabled(response.body)
                if response.code == 403:
                    raise ACLPermissionDenied(response.body)
                return json.loads(response.body)['ID']

            return self.agent.http.put(
                callback, '/v1/acl/create', params=params, data=data)

        def update(self, acl_id, name=None, type=None, rules=None, token=None):
            """
            Updates the ACL token *acl_id*. This is a privileged endpoint, and
            requires a management token. *token* will override this client's
            default token. An *ACLPermissionDenied* exception will be raised if
            a management token is not used.

            *name* is an optional name for this token.

            *type* is either 'management' or 'client'. A management token is
            effectively like a root user, and has the ability to perform any
            action including creating, modifying, and deleting ACLs. A client
            token can only perform actions as permitted by *rules*.

            *rules* is an optional `HCL`_ string for this `ACL Token`_ Rule
            Specification.

            Returns the string *acl_id* of this token on success.
            """
            params = {}
            token = token or self.agent.token
            if token:
                params['token'] = token

            payload = {'ID': acl_id}
            if name:
                payload['Name'] = name
            if type:
                assert type == 'client' or type == 'management'
                payload['Type'] = type
            if rules:
                assert isinstance(rules, str), \
                    'Only HCL encoded strings supported for the moment'
                payload['Rules'] = rules

            data = json.dumps(payload)

            def callback(response):
                if response.code == 401:
                    raise ACLDisabled(response.body)
                if response.code == 403:
                    raise ACLPermissionDenied(response.body)
                return json.loads(response.body)['ID']

            return self.agent.http.put(
                callback, '/v1/acl/update', params=params, data=data)

        def clone(self, acl_id, token=None):
            """
            Clones the ACL token *acl_id*. This is a privileged endpoint, and
            requires a management token. *token* will override this client's
            default token. An *ACLPermissionDenied* exception will be raised if
            a management token is not used.

            Returns the string of the newly created *acl_id*.
            """
            params = {}
            token = token or self.agent.token
            if token:
                params['token'] = token

            def callback(response):
                if response.code == 401:
                    raise ACLDisabled(response.body)
                if response.code == 403:
                    raise ACLPermissionDenied(response.body)
                return json.loads(response.body)['ID']

            return self.agent.http.put(
                callback, '/v1/acl/clone/%s' % acl_id, params=params)

        def destroy(self, acl_id, token=None):
            """
            Destroys the ACL token *acl_id*. This is a privileged endpoint, and
            requires a management token. *token* will override this client's
            default token. An *ACLPermissionDenied* exception will be raised if
            a management token is not used.

            Returns *True* on success.
            """
            params = {}
            token = token or self.agent.token
            if token:
                params['token'] = token

            def callback(response):
                if response.code == 401:
                    raise ACLDisabled(response.body)
                if response.code == 403:
                    raise ACLPermissionDenied(response.body)
                return json.loads(response.body)

            return self.agent.http.put(
                callback, '/v1/acl/destroy/%s' % acl_id, params=params)
