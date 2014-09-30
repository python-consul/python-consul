.. include:: ../README.rst

Clients
-------

Standard
~~~~~~~~

.. code:: python

    >>> import consul
    >>> c = consul.Consul()
    >>> c.kv.put('foo', 'bar')
    True
    >>> index, data = c.kv.get('foo')
    >>> data['Value']
    'bar'
    >>> index, data = c.kv.get('foo', index=index)
    # this will block until there's an update or a timeout

Tornado
~~~~~~~

Poll a key for updates and make it's value available on a shared configuration
object.

.. code:: python

    import consul.tornado

    class Config(object):
        def __init__(self):
            self.foo = None
            loop.add_callback(self.watch)

        @tornado.gen.coroutine
        def watch(self):
            c = consul.tornado.Consul()
            index = None
            while True:
                index, data = yield c.kv.get('foo', index=index)
                self.foo = data['Value']

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
   :undoc-members:
   :exclude-members: Service

.. autoclass:: consul.base::Consul.Agent.Service()
   :members:
   :undoc-members:
