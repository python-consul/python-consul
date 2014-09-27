# Python client for Consul (http://www.consul.io/)

[![Build Status](https://travis-ci.org/cablehead/python-consul.svg?branch=master)](https://travis-ci.org/cablehead/python-consul)[![Coverage Status](https://coveralls.io/repos/cablehead/python-consul/badge.png?branch=master)](https://coveralls.io/r/cablehead/python-consul?branch=master)

## Installation

```
    pip install python-consul
```

## Usage

### Standard

```
    >>> import consul
    >>> c = consul.Consul()
    >>> c.kv.put('foo', 'bar')
    True
    >>> index, data = c.kv.get('foo')
    >>> data['Value']
    'bar'
    >>> index, data = c.kv.get('foo', index=index)
    # this will block until there's an update and a timeout
```
