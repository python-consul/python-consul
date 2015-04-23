Change log
==========

0.3.16
------

Features
~~~~~~~~

* Add cas param for kv.delete (thanks @qix)

0.3.15
------

Features
~~~~~~~~

* Add tag parameter to health.service() (thanks @reversefold)

0.3.14
------

Features
~~~~~~~~

* add the keys and separator params to kv.get (thanks @Heuriskein)
* add support for the events api (thanks @Heuriskein!)

0.3.13
------

Features
~~~~~~~~

* add HTTP check support (thanks @JoeHazzers)
* raise ConsulException on kv.get 500 response code (thanks @jjpersch)
* add the wait argument to kv.get

0.3.12
------

Features
~~~~~~~~

* add behavior and ttl to session.create
* add session.renew

0.3.11
------

Features
~~~~~~~~

* add the health.state endpoint (thanks @pete0emerson!)
* bump test binaries to 0.5.0

0.3.9
-----

Bug Fix
~~~~~~~

* Exclude consul.aio if asyncio isn't available, avoids an error message on
  install, trying to byte compile that module

0.3.8
-----

API changes (backwards incompatible)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Reorder named arguments to be more consistent. index is always the first
  named argument, if available, and dc is now always the last named argument.

0.3.7
-----

Features
~~~~~~~~

* Add dc support for kv calls; add ability to set the default dc for an entire
  client session (thanks @angad)
* Add asyncio client (thanks @jettify)

0.3.6
-----

Features
~~~~~~~~

* Add https support (thanks @pete0emerson)
* Add wan param to agent.members (thanks @sgargan)

0.3.5
-----

Bug Fix
~~~~~~~

* Fix typo setting notes on a check (thanks @ShaheedHaque!)

0.3.4
-----

Features
~~~~~~~~

* Add support for the Agent.Check (thanks @sgargan and @ShaheedHaque)

Deprecated
~~~~~~~~~~

* health.check.ttl_pass has been moved to agent.check.ttl_pass

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
