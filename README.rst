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

    >>> import consul
    >>> c = consul.Consul()
    >>> c.kv.put('foo', 'bar')
    >>> index, data = c.kv.get('foo')
    >>> data['Value']
    >>> 'bar'


Installation
------------

::

    pip install python-consul

.. |Build Status|
   image:: https://travis-ci.org/cablehead/python-consul.svg?branch=master
   :target: https://travis-ci.org/cablehead/python-consul
.. |Coverage Status|
   image:: https://coveralls.io/repos/cablehead/python-consul/badge.png?branch=master
   :target: https://coveralls.io/r/cablehead/python-consul?branch=master
.. _Read the Docs: http://python-consul.readthedocs.org/
