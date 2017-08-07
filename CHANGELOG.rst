Change log
==========

0.7.2-dev
---------

* TBD

0.7.1
-----

* Add a common base client for shared functionality between different HTTP clients (thanks @abn!)
* Fix request quoting issue (thanks @abn)
* Fix installation issue due to aiohttp only being available for Python>=3.4.2 (thanks @abn)
* Added support for current release of aiohttp (thanks @eaterek)
* Improved Tornado example (thanks @chriswue)
* Add and use ACL token in Event.fire (thanks @illenseer)
* Add client side cert support (thanks @brocade-craig)
* Add token params to catalog register (thanks @gregdurham)
* Add support for DeregisterCriticalServiceAfter (thanks @daroot)
* Improve reliability of test suite (thanks @daroot!)
* Update CI: Add py35 and py36 to tests (thanks @Poogles)

0.7.0
-----

Features
~~~~~~~~

* Add Operator endpoint (thanks @bantonj!)

0.6.2
-----

Bug Fix
~~~~~~~

* Tornado backend encoding bug related to None values (thanks @plredmond)
* python-consul doesn't support python 2.6 (thanks @lowzj)

Maintenance
~~~~~~~~~~~

* update max ttl to 86400 to conform to consul (thanks @philloooo)
* Correct error message in ACL create/update (thanks @Crypto89)

Features
~~~~~~~~

* Catalog API should support tokens (thanks @racktear!)
* Allow enable tag override (thanks @shalev67!)

0.6.1
------

Features
~~~~~~~~

* Add the coordinate endpoint and near support on Catalog and Health Checks
  (thanks @shalev67!)
* Rework all endpoints to use a common callback handler to help ensure
  consistent handling of responses (thanks @shalev67)
* Add Query api support (thanks @shalev67)
* Add token support for the Health endpoints (thanks @morpheu!)
* Force to use UTF-8 encoding for the response with the request's client
  (thanks @maxnasonov)

Maintenance
~~~~~~~~~~~

* Migrate readthedocs links from .org to .io (thanks @adamchainz)

0.6.0
------

Features
~~~~~~~~

* Add support for the new TCP and Docker health checks (thanks @abn)
* Add support for join and force-leave (thanks @abn)
* Use standard consul environment variables to override configuration (thanks
  @amayausky)

Maintenance
~~~~~~~~~~~

* Test binaries updated to Consul 0.6.4
* Tweaks to fix small updates to Consul's API

0.4.7
------

Features
~~~~~~~~

* Add ACL token support to agent.service.register and agent.check.register

0.4.6
------

Features
~~~~~~~~

* Add health.checks endpoint, update health TODOs (thanks @cruatta!)
* Improve error when a HTTP 503 status code is returned (thanks @raboof!)
* Added index and wait parameter to event.list (thanks @max0d41!)


0.4.5
------

Features
~~~~~~~~

* Allow SSL certificate verification to be disabled (thanks @jgadling!)
* Use requests.session for performance (thanks @msabramo!)
* Support 'wait' param for all blocking queries (thanks @rmt!)
* deduplicate query string when doing deletes with the std (requests) library
  (thanks @sduthil!)

0.4.4
------

Features
~~~~~~~~

* Support creation of ALCs with explicit ID. (thanks @KyleJamesWalker)

0.4.3
------

Features
~~~~~~~~

* Support 'dc' argument to health endpoints (thanks @etuttle!)

0.4.2
------

Features
~~~~~~~~

* Add status endpoints (thanks @cruatta!)

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
