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

Wanted
~~~~~~

Adaptors for `asyncio`_, `Twisted`_ and a `thread pool`_ based adaptor.


API Documentation
-----------------

.. autoclass:: consul.Consul

consul.kv
~~~~~~~~~

.. autoclass:: consul.base::Consul.KV()
   :members:
   :undoc-members:

consul.agent
~~~~~~~~~~~~

.. autoclass:: consul.base::Consul.Agent()
   :members:
   :exclude-members: Service

.. autoclass:: consul.base::Consul.Agent.Service()
   :members:

consul.health
~~~~~~~~~~~~~

.. autoclass:: consul.base::Consul.Health()
   :members:
   :undoc-members:
   :exclude-members: Check

.. autoclass:: consul.base::Consul.Health.Check()
   :members:
   :undoc-members:

consul.acl
~~~~~~~~~~

.. autoclass:: consul.base::Consul.ACL()
   :members:
   :undoc-members:

.. _ACL Token: http://www.consul.io/docs/internals/acl.html
.. _requests: http://python-requests.org
.. _Vanilla: https://github.com/cablehead/vanilla
.. _gevent: http://www.gevent.org
.. _Tornado: http://www.tornadoweb.org
.. _gen.coroutine: http://tornado.readthedocs.org/en/latest/gen.html

.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _Twisted: https://twistedmatrix.com/trac/
.. _thread pool: https://docs.python.org/2/library/threading.html
