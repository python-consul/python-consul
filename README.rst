Python client for `Consul.io <http://www.consul.io/>`_
======================================================

Documentation
-------------

`Read the Docs`_

Status
------

|Build Status|

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


Alternatively you can create a client from the same `environment variables`_ that
the consul command line client uses. e.g. CONSUL_HTTP_ADDR, CONSUL_HTTP_TOKEN.

.. code:: python

    import consul

    c = consul.Consul.from_env()

    c.agent.self()


Installation
------------

::

    pip install python-consul
    
**Note:** When using python-consul library in environment with proxy server, setting of ``http_proxy``, ``https_proxy`` and ``no_proxy`` environment variables can be required for proper functionality.

.. |Build Status|
   image:: https://img.shields.io/travis/cablehead/python-consul.svg?style=flat-square
   :target: https://travis-ci.org/cablehead/python-consul
.. |Coverage Status|
   image:: https://img.shields.io/coveralls/cablehead/python-consul.svg?style=flat-square
   :target: https://coveralls.io/r/cablehead/python-consul?branch=master
.. _Read the Docs: https://python-consul.readthedocs.io/
.. _environment variables: https://www.consul.io/docs/commands/index.html#environment-variables

Status
------

There's a few API endpoints still to go to expose all features available in
Consul v0.6.0. If you need an endpoint that's not in the documentation, just
open an issue and I'll try and add it straight away.

Mailing List
------------

- https://groups.google.com/forum/#!forum/python-consul

Contributing
------------

python-consul is currently maintained by:

- @matusvalo
- @abn
- @cablehead

Please reach out if you're interested in being a maintainer as well. Otherwise,
open a PR or Issue we'll try and respond as quickly as we're able.

Issue Labels
~~~~~~~~~~~~

:today!: Some triaging is in progress and this issue should be taken care of in
         a couple of hours!

:priority: There's a clear need to address this issue and it's likely a core
           contributor will take it on. Opening a PR for these is greatly
           appreciated!

:help wanted: This issue makes sense and would be useful. It's unlikely a core
              contributor will get to this though, so if you'd like to see it
              addressed please open a PR.

:question: The need for the issue isn't clear or needs clarification, so please
           follow up.  Issues in this state for a few months, without
           responses will likely will be closed.

PRs
~~~

Pull requests are very much appreciated! When you create a PR please ensure:

#. All current tests pass, including flake8
#. To add tests for your new features, if reasonable
#. To add docstrings for new api features you add and if needed link to these
   docstrings from the sphinx documentation

Releases
~~~~~~~~

.. code:: bash

    # release the current version, eg: 0.6.1-dev -> 0.6.1
    bumpversion release

    # prepare the next patch (z-stream) version, eg: 0.6.1 -> 0.6.2-dev
    bumpversion --no-tag patch

    # else, prepare the next minor (y-stream) version, eg: 0.6.1 -> 0.7.0-dev
    bumpversion --no-tag minor
