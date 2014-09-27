# Python client for Consul (http://www.consul.io/)

[![Build Status](https://travis-ci.org/cablehead/python-consul.svg?branch=master)](https://travis-ci.org/cablehead/python-consul)[![Coverage Status](https://coveralls.io/repos/cablehead/python-consul/badge.png?branch=master)](https://coveralls.io/r/cablehead/python-consul?branch=master)

## Install

```
    pip install python-consul
```

## Usage

### Standard

```python

    >>> import consul
    >>> c = consul.Consul()
    >>> c.kv.put('foo', 'bar')
    True
    >>> index, data = c.kv.get('foo')
    >>> data['Value']
    'bar'
    >>> index, data = c.kv.get('foo', index=index)
    # this will block until there's an update or a timeout
```

### Tornado

Poll a key for updates

```python

    import consul.tornado

    c = consul.tornado.Consul()

    @tornado.gen.coroutine
    def watch():
        index = None
        while True:
            index, data = yield c.kv.get('foo', index=index)
            print data['Value']

    loop.add_callback(watch)
```
