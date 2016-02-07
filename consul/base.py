import collections
import logging
import base64
import json
import os

import six


log = logging.getLogger(__name__)


class ConsulException(Exception):
    pass


class ACLDisabled(ConsulException):
    pass


class ACLPermissionDenied(ConsulException):
    pass


class NotFound(ConsulException):
    pass


class Timeout(ConsulException):
    pass


#
# Convenience to define checks

class Check(object):
    """
    There are three different kinds of checks: script, http and ttl
    """
    @classmethod
    def script(klass, script, interval):
        """
        Run *script* every *interval* (e.g. "10s") to peform health check
        """
        return {'script': script, 'interval': interval}

    @classmethod
    def http(klass, url, interval, timeout=None):
        """
        Peform a HTTP GET against *url* every *interval* (e.g. "10s") to peform
        health check with an option *timeout*
        """
        ret = {'http': url, 'interval': interval}
        if timeout:
            ret['timeout'] = timeout
        return ret

    @classmethod
    def tcp(klass, host, port, interval, timeout=None):
        """
        Attempt to establish a tcp connection to the specified *host* and
        *port* at a specified *interval* with optional *timeout*
        """
        ret = {
            'tcp': '{host:s}:{port:d}'.format(host=host, port=port),
            'interval': interval
        }
        if timeout:
            ret['timeout'] = timeout
        return ret

    @classmethod
    def ttl(klass, ttl):
        """
        Set check to be marked as critical after *ttl* (e.g. "10s") unless the
        check is periodically marked as passing.
        """
        return {'ttl': ttl}

    @classmethod
    def docker(klass, container_id, shell, script, interval):
        """
        Invoke *script* packaged within a running docker container with
        *container_id* at a specified specified *interval* on the configured
        *shell* using the Docker Exec API
        """
        ret = {
            'docker_container_id': container_id,
            'shell': shell,
            'script': script,
            'interval': interval
        }
        return ret

    @classmethod
    def _compat(
            self,
            script=None,
            interval=None,
            ttl=None,
            http=None,
            timeout=None):

        if not script and not http and not ttl:
            return {}

        log.warn(
            'DEPRECATED: use consul.Check.script/http/ttl to specify check')

        ret = {'check': {}}

        if script:
            assert interval and not (ttl or http)
            ret['check'] = {'script': script, 'interval': interval}
        if ttl:
            assert not (interval or script or http)
            ret['check'] = {'ttl': ttl}
        if http:
            assert interval and not (script or ttl)
            ret['check'] = {'http': http, 'interval': interval}
        if timeout:
            assert http
            ret['check']['timeout'] = timeout

        return ret


Response = collections.namedtuple('Response', ['code', 'headers', 'body'])


def callback(
        map=None,
        is_200=False,
        is_json=False,
        index=False,
        one=False,
        allow_404=True):

    def cb(response):
        if response.code >= 500 and response.code < 600:
            raise ConsulException("%d %s" % (response.code, response.body))
        if response.code == 403:
            raise ACLPermissionDenied(response.body)
        if response.code == 404 and not allow_404:
            raise NotFound(response.body)
        if is_200:
            data = response.code == 200
        elif is_json:
            data = json.loads(response.body)
        else:
            data = response
        if one:
            if data == []:
                data = None
            if data is not None:
                data = data[0]
        if map:
            data = map(data)
        if index:
            return response.headers['X-Consul-Index'], data
        return data
    return cb


class Consul(object):
    def __init__(
            self,
            host='127.0.0.1',
            port=8500,
            token=None,
            scheme='http',
            consistency='default',
            dc=None,
            verify=True):
        """
        *token* is an optional `ACL token`_. If supplied it will be used by
        default for all requests made with this client session. It's still
        possible to override this token by passing a token explicitly for a
        request.

        *consistency* sets the consistency mode to use by default for all reads
        that support the consistency option. It's still possible to override
        this by passing explicitly for a given request. *consistency* can be
        either 'default', 'consistent' or 'stale'.

        *dc* is the datacenter that this agent will communicate with.
        By default the datacenter of the host is used.

        *verify* is whether to verify the SSL certificate for HTTPS requests
        """

        # TODO: Status

        if os.getenv('CONSUL_HTTP_ADDR'):
            host, port = os.getenv('CONSUL_HTTP_ADDR').split(':')
        use_ssl = os.getenv('CONSUL_HTTP_SSL')
        if use_ssl is not None:
            scheme = 'https' if use_ssl == 'true' else 'http'
        if os.getenv('CONSUL_HTTP_SSL_VERIFY') is not None:
            verify = os.getenv('CONSUL_HTTP_SSL_VERIFY') == 'true'

        self.http = self.connect(host, port, scheme, verify)
        self.token = os.getenv('CONSUL_HTTP_TOKEN', token)
        self.scheme = scheme
        self.dc = dc
        assert consistency in ('default', 'consistent', 'stale'), \
            'consistency must be either default, consistent or state'
        self.consistency = consistency

        self.event = Consul.Event(self)
        self.kv = Consul.KV(self)
        self.agent = Consul.Agent(self)
        self.catalog = Consul.Catalog(self)
        self.health = Consul.Health(self)
        self.session = Consul.Session(self)
        self.acl = Consul.ACL(self)
        self.status = Consul.Status(self)

    class Event(object):
        """
        The event command provides a mechanism to fire a custom user event to
        an entire datacenter. These events are opaque to Consul, but they can
        be used to build scripting infrastructure to do automated deploys,
        restart services, or perform any other orchestration action.

        Unlike most Consul data, which is replicated using consensus, event
        data is purely peer-to-peer over gossip.

        This means it is not persisted and does not have a total ordering. In
        practice, this means you cannot rely on the order of message delivery.
        An advantage however is that events can still be used even in the
        absence of server nodes or during an outage."""
        def __init__(self, agent):
            self.agent = agent

        def fire(
                self,
                name,
                body="",
                node=None,
                service=None,
                tag=None):
            """
            Sends an event to Consul's gossip protocol.

            *name* is the Consul-opaque name of the event. This can be filtered
            on in calls to list, below

            *body* is the Consul-opaque body to be delivered with the event.
             From the Consul documentation:
                The underlying gossip also sets limits on the size of a user
                event message. It is hard to give an exact number, as it
                depends on various parameters of the event, but the payload
                should be kept very small (< 100 bytes). Specifying too large
                of an event will return an error.

            *node*, *service*, and *tag* are regular expressions which remote
            agents will filter against to determine if they should store the
            event
            """
            assert not name.startswith('/'), \
                'keys should not start with a forward slash'
            params = {}
            if node is not None:
                params['node'] = node
            if service is not None:
                params['service'] = service
            if tag is not None:
                params['tag'] = tag

            return self.agent.http.put(
                callback(is_json=True),
                '/v1/event/fire/%s' % name, params=params, data=body)

        def list(
                self,
                name=None,
                index=None,
                wait=None):
            """
            Returns a tuple of (*index*, *events*)
                Note: Since Consul's event protocol uses gossip, there is no
                ordering, and instead index maps to the newest event that
                matches the query.

            *name* is the type of events to list, if None, lists all available.

            *index* is the current event Consul index, suitable for making
            subsequent calls to wait for changes since this query was last run.
            Check https://consul.io/docs/agent/http/event.html#event_list for
            more infos about indexes on events.

            *wait* the maximum duration to wait (e.g. '10s') to retrieve
            a given index. This parameter is only applied if *index* is also
            specified. the wait time by default is 5 minutes.

            Consul agents only buffer the most recent entries. The current
            buffer size is 256, but this value could change in the future.

            Each *event* looks like this::

                {
                      {
                        "ID": "b54fe110-7af5-cafc-d1fb-afc8ba432b1c",
                        "Name": "deploy",
                        "Payload": "1609030",
                        "NodeFilter": "",
                        "ServiceFilter": "",
                        "TagFilter": "",
                        "Version": 1,
                        "LTime": 19
                      },
                }
            """
            params = {}
            if name is not None:
                params['name'] = name
            if index:
                params['index'] = index
                if wait:
                    params['wait'] = wait

            def callback(response):
                data = json.loads(response.body)
                for item in data:
                    if item.get('Payload') is not None:
                        item['Payload'] = base64.b64decode(item['Payload'])
                return response.headers['X-Consul-Index'], data

            return self.agent.http.get(
                callback, '/v1/event/list', params=params)

    class KV(object):
        """
        The KV endpoint is used to expose a simple key/value store. This can be
        used to store service configurations or other meta data in a simple
        way.
        """
        def __init__(self, agent):
            self.agent = agent

        def get(
                self,
                key,
                index=None,
                recurse=False,
                wait=None,
                token=None,
                consistency=None,
                keys=False,
                separator=None,
                dc=None):
            """
            Returns a tuple of (*index*, *value[s]*)

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *wait* the maximum duration to wait (e.g. '10s') to retrieve
            a given index. this parameter is only applied if *index* is also
            specified. the wait time by default is 5 minutes.

            *token* is an optional `ACL token`_ to apply to this request.

            *keys* is a boolean which, if True, says to return a flat list of
            keys without values or other metadata. *separator* can be used
            with *keys* to list keys only up to a given separator character.

            *dc* is the optional datacenter that you wish to communicate with.
            If None is provided, defaults to the agent's datacenter.

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

            Note, if the requested key does not exists *(index, None)* is
            returned. It's then possible to long poll on the index for when the
            key is created.
            """
            assert not key.startswith('/'), \
                'keys should not start with a forward slash'
            params = {}
            if index:
                params['index'] = index
                if wait:
                    params['wait'] = wait
            if recurse:
                params['recurse'] = '1'
            token = token or self.agent.token
            if token:
                params['token'] = token
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc
            if keys:
                params['keys'] = True
            if separator:
                params['separator'] = separator
            consistency = consistency or self.agent.consistency
            if consistency in ('consistent', 'stale'):
                params[consistency] = '1'

            def callback(response):
                if response.code == 500:
                    raise ConsulException(response.body)
                elif response.code == 404:
                    data = None
                else:
                    data = json.loads(response.body)
                    if not keys:
                        for item in data:
                            if item.get('Value') is not None:
                                item['Value'] = base64.b64decode(item['Value'])
                        if not recurse:
                            data = data[0]
                return response.headers['X-Consul-Index'], data

            return self.agent.http.get(
                callback, '/v1/kv/%s' % key, params=params)

        def put(
                self,
                key,
                value,
                cas=None,
                flags=None,
                acquire=None,
                release=None,
                token=None,
                dc=None):
            """
            Sets *key* to the given *value*.

            *value* can either be None (useful for marking a key as a
            directory) or any string type, including binary data (e.g. a
            msgpack'd data structure)

            The optional *cas* parameter is used to turn the PUT into a
            Check-And-Set operation. This is very useful as it allows clients
            to build more complex syncronization primitives on top. If the
            index is 0, then Consul will only put the key if it does not
            already exist. If the index is non-zero, then the key is only set
            if the index matches the ModifyIndex of that key.

            An optional *flags* can be set. This can be used to specify an
            unsigned value between 0 and 2^64-1.

            *acquire* is an optional session_id. if supplied a lock acquisition
            will be attempted.

            *release* is an optional session_id. if supplied a lock release
            will be attempted.

            *token* is an optional `ACL token`_ to apply to this request. If
            the token's policy is not allowed to write to this key an
            *ACLPermissionDenied* exception will be raised.

            *dc* is the optional datacenter that you wish to communicate with.
            If None is provided, defaults to the agent's datacenter.

            The return value is simply either True or False. If False is
            returned, then the update has not taken place.
            """
            assert not key.startswith('/'), \
                'keys should not start with a forward slash'
            assert value is None or \
                isinstance(value, (six.string_types, six.binary_type)), \
                "value should be None or a string / binary data"

            params = {}
            if cas is not None:
                params['cas'] = cas
            if flags is not None:
                params['flags'] = flags
            if acquire:
                params['acquire'] = acquire
            if release:
                params['release'] = release
            token = token or self.agent.token
            if token:
                params['token'] = token
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc
            return self.agent.http.put(
                callback(is_json=True),
                '/v1/kv/%s' % key, params=params, data=value)

        def delete(self, key, recurse=None, cas=None, token=None, dc=None):
            """
            Deletes a single key or if *recurse* is True, all keys sharing a
            prefix.

            *cas* is an optional flag is used to turn the DELETE into a
            Check-And-Set operation. This is very useful as a building block
            for more complex synchronization primitives. Unlike PUT, the index
            must be greater than 0 for Consul to take any action: a 0 index
            will not delete the key. If the index is non-zero, the key is only
            deleted if the index matches the ModifyIndex of that key.

            *token* is an optional `ACL token`_ to apply to this request. If
            the token's policy is not allowed to delete to this key an
            *ACLPermissionDenied* exception will be raised.

            *dc* is the optional datacenter that you wish to communicate with.
            If None is provided, defaults to the agent's datacenter.
            """
            assert not key.startswith('/'), \
                'keys should not start with a forward slash'

            params = {}
            if recurse:
                params['recurse'] = '1'
            if cas is not None:
                params['cas'] = cas
            token = token or self.agent.token
            if token:
                params['token'] = token
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc

            def callback(response):
                if response.code == 403:
                    raise ACLPermissionDenied(response.body)
                return json.loads(response.body)

            return self.agent.http.delete(
                callback, '/v1/kv/%s' % key, params=params)

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
            self.check = Consul.Agent.Check(agent)

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

        def checks(self):
            """
            Returns all the checks that are registered with the local agent.
            These checks were either provided through configuration files, or
            added dynamically using the HTTP API. Similar to services,
            the checks known by the agent may be different than those
            reported by the Catalog. This is usually due to changes being made
            while there is no leader elected. The agent performs active
            anti-entropy, so in most situations everything will be in sync
            within a few seconds.
            """
            return self.agent.http.get(
                lambda x: json.loads(x.body), '/v1/agent/checks')

        def members(self, wan=False):
            """
            Returns all the members that this agent currently sees. This may
            vary by agent, use the nodes api of Catalog to retrieve a cluster
            wide consistent view of members.

            For agents running in server mode, setting *wan* to *True* returns
            the list of WAN members instead of the LAN members which is
            default.
            """
            params = {}
            if wan:
                params['wan'] = 1

            return self.agent.http.get(
                lambda x: json.loads(x.body),
                '/v1/agent/members',
                params=params)

        def maintenance(self, enable, reason=None):
            """
            The node maintenance endpoint can place the agent into
            "maintenance mode".

            *enable* is either 'true' or 'false'. 'true' enables maintenance
            mode, 'false' disables maintenance mode.

            *reason* is an optional string. This is simply to aid human
            operators.
            """

            params = {}

            params['enable'] = enable
            if reason:
                params['reason'] = reason

            return self.agent.http.put(
                lambda x: x.code == 200,
                '/v1/agent/maintenance',
                params=params)

        def join(self, address, wan=False):
            """
            This endpoint instructs the agent to attempt to connect to a
            given address.

            *address* is the ip to connect to.

            *wan* is either 'true' or 'false'. For agents running in server
            mode, 'true' causes the agent to attempt to join using the WAN
            pool. Default is 'false'.
            """

            params = {}

            if wan:
                params['wan'] = 1

            return self.agent.http.get(
                lambda x: x.code == 200,
                '/v1/agent/join/%s' % address,
                params=params)

        def force_leave(self, node):
            """
            This endpoint instructs the agent to force a node into the left
            state. If a node fails unexpectedly, then it will be in a failed
            state. Once in the failed state, Consul will attempt to reconnect,
            and the services and checks belonging to that node will not be
            cleaned up. Forcing a node into the left state allows its old
            entries to be removed.

            *node* is the node to change state for.
            """

            return self.agent.http.get(
                lambda x: x.code == 200,
                '/v1/agent/force-leave/%s' % node)

        class Service(object):
            def __init__(self, agent):
                self.agent = agent

            def register(
                    self,
                    name,
                    service_id=None,
                    address=None,
                    port=None,
                    tags=None,
                    check=None,
                    token=None,
                    # *deprecated* use check parameter
                    script=None,
                    interval=None,
                    ttl=None,
                    http=None,
                    timeout=None):
                """
                Add a new service to the local agent. There is more
                documentation on services
                `here <http://www.consul.io/docs/agent/services.html>`_.

                *name* is the name of the service.

                If the optional *service_id* is not provided it is set to
                *name*. You cannot have duplicate *service_id* entries per
                agent, so it may be necessary to provide one.

                *address* will default to the address of the agent if not
                provided.

                An optional health *check* can be created for this service is
                one of `Check.script`_, `Check.http`_, `Check.tcp`_,
                `Check.ttl`_ or `Check.docker`_.

                *token* is an optional `ACL token`_ to apply to this request.
                Note this call will return successful even if the token doesn't
                have permissions to register this service.

                *script*, *interval*, *ttl*, *http*, and *timeout* arguments
                are deprecated. use *check* instead.
                """
                payload = {'name': name}
                if service_id:
                    payload['id'] = service_id
                if address:
                    payload['address'] = address
                if port:
                    payload['port'] = port
                if tags:
                    payload['tags'] = tags

                if check:
                    payload['check'] = check

                else:
                    payload.update(Check._compat(
                        script=script,
                        interval=interval,
                        ttl=ttl,
                        http=http,
                        timeout=timeout))

                params = {}
                token = token or self.agent.token
                if token:
                    params['token'] = token

                return self.agent.http.put(
                    lambda x: x.code == 200,
                    '/v1/agent/service/register',
                    params=params,
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

            def maintenance(self, service_id, enable, reason=None):
                """
                The service maintenance endpoint allows placing a given service
                into "maintenance mode".

                *service_id* is the id of the service that is to be targeted
                for maintenance.

                *enable* is either 'true' or 'false'. 'true' enables
                maintenance mode, 'false' disables maintenance mode.

                *reason* is an optional string. This is simply to aid human
                operators.
                """

                params = {}

                params['enable'] = enable
                if reason:
                    params['reason'] = reason

                return self.agent.http.put(
                    lambda x: x.code == 200,
                    '/v1/agent/service/maintenance/{0}'.format(service_id),
                    params=params)

        class Check(object):
            def __init__(self, agent):
                self.agent = agent

            def register(
                    self,
                    name,
                    check=None,
                    check_id=None,
                    notes=None,
                    service_id=None,
                    token=None,
                    # *deprecated* use check parameter
                    script=None,
                    interval=None,
                    ttl=None,
                    http=None,
                    timeout=None):
                """
                Register a new check with the local agent. More documentation
                on checks can be found `here
                <http://www.consul.io/docs/agent/checks.html>`_.

                *name* is the name of the check.

                *check* is one of `Check.script`_, `Check.http`_, `Check.tcp`_
                `Check.ttl`_ or `Check.docker`_ and is required.

                If the optional *check_id* is not provided it is set to *name*.
                *check_id* must be unique for this agent.

                *notes* is not used by Consul, and is meant to be human
                readable.

                Optionally, a *service_id* can be specified to associate a
                registered check with an existing service.

                *token* is an optional `ACL token`_ to apply to this request.
                Note this call will return successful even if the token doesn't
                have permissions to register this check.

                *script*, *interval*, *ttl*, *http*, and *timeout* arguments
                are deprecated. use *check* instead.

                Returns *True* on success.
                """
                payload = {'name': name}

                assert check or script or ttl or http, \
                    'check is required'

                if check:
                    payload.update(check)

                else:
                    payload.update(Check._compat(
                        script=script,
                        interval=interval,
                        ttl=ttl,
                        http=http,
                        timeout=timeout)['check'])

                if check_id:
                    payload['id'] = check_id
                if notes:
                    payload['notes'] = notes
                if service_id:
                    payload['serviceid'] = service_id

                params = {}
                token = token or self.agent.token
                if token:
                    params['token'] = token

                return self.agent.http.put(
                    lambda x: x.code == 200,
                    '/v1/agent/check/register',
                    params=params,
                    data=json.dumps(payload))

            def deregister(self, check_id):
                """
                Remove a check from the local agent.
                """
                return self.agent.http.get(
                    lambda x: x.code == 200,
                    '/v1/agent/check/deregister/%s' % check_id)

            def ttl_pass(self, check_id, notes=None):
                """
                Mark a ttl based check as passing. Optional notes can be
                attached to describe the status of the check.
                """
                params = {}
                if notes:
                    params['note'] = notes

                return self.agent.http.get(
                    lambda x: x.code == 200,
                    '/v1/agent/check/pass/%s' % check_id,
                    params=params)

            def ttl_fail(self, check_id, notes=None):
                """
                Mark a ttl based check as failing. Optional notes can be
                attached to describe why check is failing. The status of the
                check will be set to critical and the ttl clock will be reset.
                """
                params = {}
                if notes:
                    params['note'] = notes

                return self.agent.http.get(
                    lambda x: x.code == 200,
                    '/v1/agent/check/fail/%s' % check_id,
                    params=params)

            def ttl_warn(self, check_id, notes=None):
                """
                Mark a ttl based check with warning. Optional notes can be
                attached to describe the warning. The status of the
                check will be set to warn and the ttl clock will be reset.
                """
                params = {}
                if notes:
                    params['note'] = notes

                return self.agent.http.get(
                    lambda x: x.code == 200,
                    '/v1/agent/check/warn/%s' % check_id,
                    params=params)

    class Catalog(object):
        def __init__(self, agent):
            self.agent = agent

        def register(self, node, address, service=None, check=None, dc=None):
            """
            A low level mechanism for directly registering or updating entries
            in the catalog. It is usually recommended to use
            agent.service.register and agent.check.register, as they are
            simpler and perform anti-entropy.

            *node* is the name of the node to register.

            *address* is the ip of the node.

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

            *dc* is the datacenter of the node and defaults to this agents
            datacenter.

            This manipulates the health check entry, but does not setup a
            script or TTL to actually update the status. The full documentation
            is `here <https://consul.io/docs/agent/http.html#catalog>`_.

            Returns *True* on success.
            """
            data = {'node': node, 'address': address}
            dc = dc or self.agent.dc
            if dc:
                data['datacenter'] = dc
            if service:
                data['service'] = service
            if check:
                data['check'] = check
            return self.agent.http.put(
                callback(is_200=True),
                '/v1/catalog/register', data=json.dumps(data))

        def deregister(self, node, service_id=None, check_id=None, dc=None):
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
            dc = dc or self.agent.dc
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

        def nodes(self, index=None, wait=None, consistency=None, dc=None):
            """
            Returns a tuple of (*index*, *nodes*) of all nodes known
            about in the *dc* datacenter. *dc* defaults to the current
            datacenter of this agent.

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *wait* the maximum duration to wait (e.g. '10s') to retrieve
            a given index. this parameter is only applied if *index* is also
            specified. the wait time by default is 5 minutes.

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
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc
            if index:
                params['index'] = index
                if wait:
                    params['wait'] = wait
            consistency = consistency or self.agent.consistency
            if consistency in ('consistent', 'stale'):
                params[consistency] = '1'
            return self.agent.http.get(
                callback(is_json=True, index=True),
                '/v1/catalog/nodes', params=params)

        def services(self, index=None, wait=None, consistency=None, dc=None):
            """
            Returns a tuple of (*index*, *services*) of all services known
            about in the *dc* datacenter. *dc* defaults to the current
            datacenter of this agent.

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *wait* the maximum duration to wait (e.g. '10s') to retrieve
            a given index. this parameter is only applied if *index* is also
            specified. the wait time by default is 5 minutes.

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
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc
            if index:
                params['index'] = index
                if wait:
                    params['wait'] = wait
            consistency = consistency or self.agent.consistency
            if consistency in ('consistent', 'stale'):
                params[consistency] = '1'
            return self.agent.http.get(
                callback(is_json=True, index=True),
                '/v1/catalog/services', params=params)

        def node(self, node, index=None, wait=None, consistency=None, dc=None):
            """
            Returns a tuple of (*index*, *services*) of all services provided
            by *node*.

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *wait* the maximum duration to wait (e.g. '10s') to retrieve
            a given index. this parameter is only applied if *index* is also
            specified. the wait time by default is 5 minutes.

            *consistency* can be either 'default', 'consistent' or 'stale'. if
            not specified *consistency* will the consistency level this client
            was configured with.

            *dc* is the datacenter of the node and defaults to this agents
            datacenter.

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
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc
            if index:
                params['index'] = index
                if wait:
                    params['wait'] = wait
            consistency = consistency or self.agent.consistency
            if consistency in ('consistent', 'stale'):
                params[consistency] = '1'
            return self.agent.http.get(
                callback(is_json=True, index=True),
                '/v1/catalog/node/%s' % node, params=params)

        def service(
                self,
                service,
                index=None,
                wait=None,
                tag=None,
                consistency=None,
                dc=None):
            """
            Returns a tuple of (*index*, *nodes*) of the nodes providing
            *service* in the *dc* datacenter. *dc* defaults to the current
            datacenter of this agent.

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *wait* the maximum duration to wait (e.g. '10s') to retrieve
            a given index. this parameter is only applied if *index* is also
            specified. the wait time by default is 5 minutes.

            If *tag* is provided, the list of nodes returned will be filtered
            by that tag.

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
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc
            if tag:
                params['tag'] = tag
            if index:
                params['index'] = index
                if wait:
                    params['wait'] = wait
            consistency = consistency or self.agent.consistency
            if consistency in ('consistent', 'stale'):
                params[consistency] = '1'
            return self.agent.http.get(
                callback(is_json=True, index=True),
                '/v1/catalog/service/%s' % service, params=params)

    class Health(object):
        # TODO: All of the health endpoints support all consistency modes
        def __init__(self, agent):
            self.agent = agent

        def service(self,
                    service,
                    index=None,
                    wait=None,
                    passing=None,
                    tag=None,
                    dc=None):
            """
            Returns a tuple of (*index*, *nodes*)

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *wait* the maximum duration to wait (e.g. '10s') to retrieve
            a given index. this parameter is only applied if *index* is also
            specified. the wait time by default is 5 minutes.

            *nodes* are the nodes providing the given service.

            Calling with *passing* set to True will filter results to only
            those nodes whose checks are currently passing.

            Calling with *tag* will filter the results by tag.

            *dc* is the datacenter of the node and defaults to this agents
            datacenter.
            """
            params = {}
            if index:
                params['index'] = index
                if wait:
                    params['wait'] = wait
            if passing:
                params['passing'] = '1'
            if tag is not None:
                params['tag'] = tag
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc

            def callback(response):
                data = json.loads(response.body)
                return response.headers['X-Consul-Index'], data

            return self.agent.http.get(
                callback,
                '/v1/health/service/%s' % service, params=params)

        def checks(self, service, index=None, wait=None, dc=None):
            """
            Returns a tuple of (*index*, *checks*) with *checks* being the
            checks associated with the service.

            *service* is the name of the service being checked.

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *wait* the maximum duration to wait (e.g. '10s') to retrieve
            a given index. this parameter is only applied if *index* is also
            specified. the wait time by default is 5 minutes.

            *dc* is the datacenter of the node and defaults to this agents
            datacenter.

            """
            params = {}
            if index:
                params['index'] = index
                if wait:
                    params['wait'] = wait
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc

            def callback(response):
                data = json.loads(response.body)
                return response.headers['X-Consul-Index'], data

            return self.agent.http.get(
                callback,
                '/v1/health/checks/%s' % service, params=params)

        def state(self, name, index=None, wait=None, dc=None):
            """
            Returns a tuple of (*index*, *nodes*)

            *name* is a supported state. From the Consul docs:

                The supported states are any, unknown, passing, warning, or
                critical. The any state is a wildcard that can be used to
                return all checks.

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *wait* the maximum duration to wait (e.g. '10s') to retrieve
            a given index. this parameter is only applied if *index* is also
            specified. the wait time by default is 5 minutes.

            *dc* is the datacenter of the node and defaults to this agents
            datacenter.

            *nodes* are the nodes providing the given service.
            """
            assert name in ['any', 'unknown', 'passing', 'warning', 'critical']
            params = {}
            if index:
                params['index'] = index
                if wait:
                    params['wait'] = wait
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc

            def callback(response):
                data = json.loads(response.body)
                return response.headers['X-Consul-Index'], data

            return self.agent.http.get(
                callback,
                '/v1/health/state/%s' % name, params=params)

        def node(self, node, index=None, wait=None, dc=None):
            """
            Returns a tuple of (*index*, *checks*)

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *wait* the maximum duration to wait (e.g. '10s') to retrieve
            a given index. this parameter is only applied if *index* is also
            specified. the wait time by default is 5 minutes.

            *dc* is the datacenter of the node and defaults to this agents
            datacenter.

            *nodes* are the nodes providing the given service.
            """
            params = {}
            if index:
                params['index'] = index
                if wait:
                    params['wait'] = wait
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc

            def callback(response):
                data = json.loads(response.body)
                return response.headers['X-Consul-Index'], data

            return self.agent.http.get(
                callback,
                '/v1/health/node/%s' % node, params=params)

    class Session(object):
        def __init__(self, agent):
            self.agent = agent

        def create(
                self,
                name=None,
                node=None,
                checks=None,
                lock_delay=15,
                behavior='release',
                ttl=None,
                dc=None):
            """
            Creates a new session. There is more documentation for sessions
            `here <https://consul.io/docs/internals/sessions.html>`_.

            *name* is an optional human readable name for the session.

            *node* is the node to create the session on. if not provided the
            current agent's node will be used.

            *checks* is a list of checks to associate with the session. if not
            provided it defaults to the *serfHealth* check. It is highly
            recommended that, if you override this list, you include the
            default *serfHealth*.

            *lock_delay* is an integer of seconds.

            *behavior* can be set to either 'release' or 'delete'. This
            controls the behavior when a session is invalidated. By default,
            this is 'release', causing any locks that are held to be released.
            Changing this to 'delete' causes any locks that are held to be
            deleted. 'delete' is useful for creating ephemeral key/value
            entries.

            when *ttl* is provided, the session is invalidated if it is not
            renewed before the TTL expires.  If specified, it is an integer of
            seconds.  Currently it must be between 10 and 3600 seconds.

            By default the session will be created in the current datacenter
            but an optional *dc* can be provided.

            Returns the string *session_id* for the session.
            """
            params = {}
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc
            data = {}
            if name:
                data['name'] = name
            if node:
                data['node'] = node
            if checks is not None:
                data['checks'] = checks
            if lock_delay != 15:
                data['lockdelay'] = '%ss' % lock_delay
            assert behavior in ('release', 'delete'), \
                'behavior must be release or delete'
            if behavior != 'release':
                data['behavior'] = behavior
            if ttl:
                assert 10 <= ttl <= 3600
                data['ttl'] = '%ss' % ttl
            if data:
                data = json.dumps(data)
            else:
                data = ''
            return self.agent.http.put(
                callback(lambda x: json.loads(x.body)['ID']),
                '/v1/session/create', params=params, data=data)

        def destroy(self, session_id, dc=None):
            """
            Destroys the session *session_id*

            Returns *True* on success.
            """
            params = {}
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc
            return self.agent.http.put(
                callback(is_200=True),
                '/v1/session/destroy/%s' % session_id, params=params)

        def list(self, index=None, wait=None, consistency=None, dc=None):
            """
            Returns a tuple of (*index*, *sessions*) of all active sessions in
            the *dc* datacenter. *dc* defaults to the current datacenter of
            this agent.

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *wait* the maximum duration to wait (e.g. '10s') to retrieve
            a given index. this parameter is only applied if *index* is also
            specified. the wait time by default is 5 minutes.

            *consistency* can be either 'default', 'consistent' or 'stale'. if
            not specified *consistency* will the consistency level this client
            was configured with.

            The response looks like this::

                (index, [
                    {
                        "LockDelay": 1.5e+10,
                        "Checks": [
                            "serfHealth"
                        ],
                        "Node": "foobar",
                        "ID": "adf4238a-882b-9ddc-4a9d-5b6758e4159e",
                        "CreateIndex": 1086449
                    },
                  ...
               ])
            """
            params = {}
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc
            if index:
                params['index'] = index
                if wait:
                    params['wait'] = wait
            consistency = consistency or self.agent.consistency
            if consistency in ('consistent', 'stale'):
                params[consistency] = '1'
            return self.agent.http.get(
                callback(is_json=True, index=True),
                '/v1/session/list', params=params)

        def node(self, node, index=None, wait=None, consistency=None, dc=None):
            """
            Returns a tuple of (*index*, *sessions*) as per *session.list*, but
            filters the sessions returned to only those active for *node*.

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *wait* the maximum duration to wait (e.g. '10s') to retrieve
            a given index. this parameter is only applied if *index* is also
            specified. the wait time by default is 5 minutes.

            *consistency* can be either 'default', 'consistent' or 'stale'. if
            not specified *consistency* will the consistency level this client
            was configured with.
            """
            params = {}
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc
            if index:
                params['index'] = index
                if wait:
                    params['wait'] = wait
            consistency = consistency or self.agent.consistency
            if consistency in ('consistent', 'stale'):
                params[consistency] = '1'
            return self.agent.http.get(
                callback(is_json=True, index=True),
                '/v1/session/node/%s' % node, params=params)

        def info(self,
                 session_id,
                 index=None,
                 wait=None,
                 consistency=None,
                 dc=None):
            """
            Returns a tuple of (*index*, *session*) for the session
            *session_id* in the *dc* datacenter. *dc* defaults to the current
            datacenter of this agent.

            *index* is the current Consul index, suitable for making subsequent
            calls to wait for changes since this query was last run.

            *wait* the maximum duration to wait (e.g. '10s') to retrieve
            a given index. this parameter is only applied if *index* is also
            specified. the wait time by default is 5 minutes.

            *consistency* can be either 'default', 'consistent' or 'stale'. if
            not specified *consistency* will the consistency level this client
            was configured with.
            """
            params = {}
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc
            if index:
                params['index'] = index
                if wait:
                    params['wait'] = wait
            consistency = consistency or self.agent.consistency
            if consistency in ('consistent', 'stale'):
                params[consistency] = '1'
            return self.agent.http.get(
                callback(is_json=True, index=True, one=True),
                '/v1/session/info/%s' % session_id, params=params)

        def renew(self, session_id, dc=None):
            """
            This is used with sessions that have a TTL, and it extends the
            expiration by the TTL.

            *dc* is the optional datacenter that you wish to communicate with.
            If None is provided, defaults to the agent's datacenter.

            Returns the session.
            """
            params = {}
            dc = dc or self.agent.dc
            if dc:
                params['dc'] = dc
            return self.agent.http.put(
                callback(is_json=True, one=True, allow_404=False),
                '/v1/session/renew/%s' % session_id, params=params)

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

        def create(self,
                   name=None,
                   type='client',
                   rules=None,
                   acl_id=None,
                   token=None):
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
                assert type in ('client', 'management'), \
                    'type must be client or management'
                payload['Type'] = type
            if rules:
                assert isinstance(rules, str), \
                    'Only HCL encoded strings supported for the moment'
                payload['Rules'] = rules
            if acl_id:
                payload['ID'] = acl_id

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
                assert type in ('client', 'management'), \
                    'type must be client or management'
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

    class Status(object):
        """
        The Status endpoints are used to get information about the status
         of the Consul cluster.
        """
        def __init__(self, agent):
            self.agent = agent

        def leader(self):
            """
            This endpoint is used to get the Raft leader for the datacenter
            in which the agent is running.
            """
            return self.agent.http.get(
                lambda x: json.loads(x.body), '/v1/status/leader')

        def peers(self):
            """
            This endpoint retrieves the Raft peers for the datacenter in which
            the the agent is running.
            """
            return self.agent.http.get(
                lambda x: json.loads(x.body), '/v1/status/peers')
