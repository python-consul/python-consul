Python client for Consul (http://www.consul.io/)
================================================

|Build Status|\ |Coverage Status|

Install
-------

::

    pip install python-consul

Usage
-----

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

.. |Build Status| image:: https://travis-ci.org/cablehead/python-consul.svg?branch=master
   :target: https://travis-ci.org/cablehead/python-consul
.. |Coverage Status| image:: https://coveralls.io/repos/cablehead/python-consul/badge.png?branch=master
   :target: https://coveralls.io/r/cablehead/python-consul?branch=master
