Change log
==========

0.3.3
-----

Features
~~~~~~~~

* Add support for the Session API (Consul.Session)

Bug Fixes
~~~~~~~~~

* Fix a bug retrieving folder nodes from the KV store
  https://github.com/cablehead/python-consul/pull/6#issue-48589128
  Thanks @zacman85

0.3.2
-----

Features
~~~~~~~~

* Add support for Python 3.4

0.3.1
-----

Features
~~~~~~~~

* Add support for the Catalog API (Consul.Catalog)
* Add ability to set a default consistency mode for an entire client session
* Add the ability to pass the consistency mode with kv.get

0.3.0
-----

Features
~~~~~~~~

* Add support for ACLs (Consul.ACL)


API changes (backwards incompatible)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* For Consul.Agent.Service.register, rename *check* argument to *script*
