Change log
==========

0.4.1
------

Features
~~~~~~~~

* Add health.node (thanks @davidbirdsong!)

0.4.0
-----

API changes (backwards incompatible)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Deprecated old health.check.ttl_pass call has been removed

* Deprecate loose parameters *script*, *interval*, *ttl*, *http* and *timeout*,
  to configure checks via agent.service.register and agent.check.register. Both
  methods now take a single argument to specify checks. A convenience
  consul.Check has been added to create checks.

0.3.20
------

Features
~~~~~~~~

* Add Node and Service Maintenance (thanks @cruatta!)

Bug Fix
~~~~~~~

* Unclosed connector Exception in consul.aio (thanks @jettify!)

0.3.19
------

Bug Fix
~~~~~~~

* Fix six dependency (thanks @pawlowskimichal!)

0.3.18
------

Features
~~~~~~~~

* Adding ability to register checks with services (thanks @cruatta!)

Bug Fix
~~~~~~~
* Fix distribution for consul.aio for python3 (thanks @mbachry!)

0.3.17
------

Features
~~~~~~~~

* Add address param to agent.service.register

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
