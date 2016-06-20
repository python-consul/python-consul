.. include:: ../README.rst

Clients
-------

This library is designed to be easily adapted for a number of clients.
Particularly asynchronous clients. The following clients are currently
supported.

Standard
~~~~~~~~

This is a standard blocking python client. It isn't particularly useful for
creating server components - but it does serve as a base. It makes use of the
`requests`_ library for http requests.

.. code:: python

    >>> import consul

    >>> c = consul.Consul()

    >>> c.kv.put('foo', 'bar')
    True

    >>> index, data = c.kv.get('foo')
    >>> data['Value']
    'bar'

    # this will block until there's an update or a timeout
    >>> index, data = c.kv.get('foo', index=index)

Vanilla
~~~~~~~

An asynchronous `Vanilla`_ plugin based on this library is available at:
https://github.com/cablehead/vanilla.consul

gevent
~~~~~~

The terribly awful thing about `gevent`_ is that anything that uses the socket
library from the python standard lib, including the `requests`_ library can be
made non-blocking via monkey patching. This means the standard python-consul
client will just work asynchronously with `gevent`_.

Tornado
~~~~~~~

There is a `Tornado`_ client which makes use of `gen.coroutine`_. The API for
this client is identical to the standard python-consul client except that you
need to *yield* the result of each API call. This client is available in
*consul.tornado*.

.. code:: python

    import consul.tornado

    class Config(object):
        def __init__(self):
            self.foo = None
            loop.add_callback(self.watch)

        @tornado.gen.coroutine
        def watch(self):
            c = consul.tornado.Consul()

            # asynchronously poll for updates
            index = None
            while True:
                index, data = yield c.kv.get('foo', index=index)
                self.foo = data['Value']

asyncio
~~~~~~~

There is a `asyncio`_ (using aiohttp_) client which works with `Python3.4` and
makes use of `asyncio.coroutine`_. The API for this client is identical to
the standard python-consul client except that you need to ``yield from`` the
result of each API call. This client is available in *consul.aio*.

.. code:: python

    import asyncio
    import consul.aio


    loop = asyncio.get_event_loop()

    @asyncio.coroutine
    def go():

        # always better to pass ``loop`` explicitly, but this
        # is not mandatory, you can relay on global event loop
        c = consul.aio.Consul(port=consul_port, loop=loop)

        # set value, same as default api but with ``yield from``
        response = yield from c.kv.put(b'foo', b'bar')
        assert response is True

        # get value
        index, data = yield from c.kv.get(b'foo')
        assert data['Value'] == b'bar'

        # delete value
        response = yield from c.kv.delete(b'foo2')
        assert response is True

    loop.run_until_complete(go())


Wanted
~~~~~~

Adaptors for `Twisted`_ and a `thread pool`_ based adaptor.

Tools
-----

Handy tools built on python-consul.

`ianitor`_
~~~~~~~~~~

`ianitor`_ is a doorkeeper for your services discovered using consul. It can
automatically register new services through consul API and manage TTL health
checks.

Example Uses
------------

ACLs
~~~~

.. code:: python

    import consul

    # master_token is a *management* token, for example the *acl_master_token*
    # you started the Consul server with
    master = consul.Consul(token=master_token)

    master.kv.put('foo', 'bar')
    master.kv.put('private/foo', 'bar')

    rules = """
        key "" {
            policy = "read"
        }
        key "private/" {
            policy = "deny"
        }
    """
    token = master.acl.create(rules=rules)

    client = consul.Consul(token=token)

    client.kv.get('foo')          # OK
    client.kv.put('foo', 'bar2')  # raises ACLPermissionDenied

    client.kv.get('private/foo')  # returns None, as though the key doesn't
                                  # exist - slightly unintuitive
    client.kv.put('private/foo', 'bar2')  # raises ACLPermissionDenied

API Documentation
-----------------

Check
~~~~~

.. autoclass:: consul.Check

Check.docker
++++++++++++

.. automethod:: consul.Check.docker

Check.script
++++++++++++

.. automethod:: consul.Check.script

Check.http
++++++++++

.. automethod:: consul.Check.http

Check.tcp
+++++++++

.. automethod:: consul.Check.tcp

Check.ttl
+++++++++

.. automethod:: consul.Check.ttl


Consul
~~~~~~

.. autoclass:: consul.Consul

Consul.kv
+++++++++

.. autoclass:: consul.base::Consul.KV()
   :members:
   :undoc-members:

Consul.agent
++++++++++++

.. autoclass:: consul.base::Consul.Agent()
   :members:
   :exclude-members: Service

.. autoclass:: consul.base::Consul.Agent.Service()
   :members:

.. autoclass:: consul.base::Consul.Agent.Check()
   :members:

Consul.catalog
++++++++++++++

.. autoclass:: consul.base::Consul.Catalog()
   :members:
   :undoc-members:

Consul.health
+++++++++++++

.. autoclass:: consul.base::Consul.Health()
   :members:
   :undoc-members:
   :exclude-members: Check

Consul.session
++++++++++++++

.. autoclass:: consul.base::Consul.Session()
   :members:
   :undoc-members:

Consul.acl
++++++++++

.. autoclass:: consul.base::Consul.ACL()
   :members:
   :undoc-members:

.. _ACL Token: http://www.consul.io/docs/internals/acl.html
.. _HCL: https://github.com/hashicorp/hcl/
.. _requests: http://python-requests.org
.. _Vanilla: https://github.com/cablehead/vanilla
.. _gevent: http://www.gevent.org
.. _Tornado: http://www.tornadoweb.org
.. _gen.coroutine: https://tornado.readthedocs.io/en/latest/gen.html
.. _asyncio.coroutine: https://docs.python.org/3/library/asyncio-task.html#coroutines
.. _aiohttp: https://github.com/KeepSafe/aiohttp
.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _Twisted: https://twistedmatrix.com/trac/
.. _thread pool: https://docs.python.org/2/library/threading.html

.. _ianitor: https://github.com/ClearcodeHQ/ianitor

Consul.event
++++++++++++

.. autoclass:: consul.base::Consul.Event()
   :members:
   :undoc-members:

Consul.status
++++++++++++++

.. autoclass:: consul.base::Consul.Status()
   :members:
   :undoc-members:
