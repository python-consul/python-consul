Python client for `Consul.io <http://www.consul.io/>`_
======================================================

Documentation
-------------

`Read the Docs`_

Status
------

|Build Status|\ |Coverage Status|

Example
-------

.. code:: python

    import consul

    c = consul.Consul()

    # poll a key for updates
    index = None
    while True:
        index, data = c.kv.get('foo', index=index)
        print data['Value']

    # in another process
    c.kv.put('foo', 'bar')

Installation
------------

::

    pip install python-consul

.. |Build Status|
   image:: https://img.shields.io/travis/cablehead/python-consul.svg?style=flat-square
   :target: https://travis-ci.org/cablehead/python-consul
.. |Coverage Status|
   image:: https://img.shields.io/coveralls/cablehead/python-consul.svg?style=flat-square
   :target: https://coveralls.io/r/cablehead/python-consul?branch=master
.. _Read the Docs: http://python-consul.readthedocs.org/

Status
------

There's a few API endpoints still to go to expose all features available in
Consul v0.5.0. If you need an endpoint that's not in the documentation, just
open an issue and I'll try and add it straight away.
