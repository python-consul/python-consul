import base64
import pytest
import six
import struct
import sys

import asyncio
import consul
import consul.aio


Check = consul.Check


@pytest.fixture
def loop(request):
    asyncio.set_event_loop(None)
    loop = asyncio.new_event_loop()

    def fin():
        loop.close()

    request.addfinalizer(fin)
    return loop


class TestAsyncioConsul(object):

    def test_kv(self, loop, consul_port):

        @asyncio.coroutine
        def main():
            c = consul.aio.Consul(port=consul_port, loop=loop)
            print(c)
            index, data = yield from c.kv.get('foo')

            print(index, data)
            assert data is None
            response = yield from c.kv.put('foo', 'bar')
            assert response is True
            index, data = yield from c.kv.get('foo')
            assert data['Value'] == six.b('bar')
            c.close()

        loop.run_until_complete(main())

    def test_consul_ctor(self, loop, consul_port):
        # same as previous but with global event loop
        @asyncio.coroutine
        def main():
            c = consul.aio.Consul(port=consul_port)
            assert c._loop is loop
            yield from c.kv.put('foo', struct.pack('i', 1000))
            index, data = yield from c.kv.get('foo')
            assert struct.unpack('i', data['Value']) == (1000,)
            c.close()

        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())

    def test_kv_binary(self, loop, consul_port):
        @asyncio.coroutine
        def main():
            c = consul.aio.Consul(port=consul_port, loop=loop)
            yield from c.kv.put('foo', struct.pack('i', 1000))
            index, data = yield from c.kv.get('foo')
            assert struct.unpack('i', data['Value']) == (1000,)
            c.close()

        loop.run_until_complete(main())

    def test_kv_missing(self, loop, consul_port):
        c = consul.aio.Consul(port=consul_port, loop=loop)

        @asyncio.coroutine
        def main():
            fut = asyncio.async(put(), loop=loop)
            yield from c.kv.put('index', 'bump')
            index, data = yield from c.kv.get('foo')
            assert data is None
            index, data = yield from c.kv.get('foo', index=index)
            assert data['Value'] == six.b('bar')
            yield from fut
            c.close()

        @asyncio.coroutine
        def put():
            yield from asyncio.sleep(2.0/100, loop=loop)
            yield from c.kv.put('foo', 'bar')

        loop.run_until_complete(main())

    def test_kv_put_flags(self, loop, consul_port):
        @asyncio.coroutine
        def main():
            c = consul.aio.Consul(port=consul_port, loop=loop)
            yield from c.kv.put('foo', 'bar')
            index, data = yield from c.kv.get('foo')
            assert data['Flags'] == 0

            response = yield from c.kv.put('foo', 'bar', flags=50)
            assert response is True
            index, data = yield from c.kv.get('foo')
            assert data['Flags'] == 50
            c.close()

        loop.run_until_complete(main())

    def test_kv_delete(self, loop, consul_port):
        @asyncio.coroutine
        def main():
            c = consul.aio.Consul(port=consul_port, loop=loop)
            yield from c.kv.put('foo1', '1')
            yield from c.kv.put('foo2', '2')
            yield from c.kv.put('foo3', '3')
            index, data = yield from c.kv.get('foo', recurse=True)
            assert [x['Key'] for x in data] == ['foo1', 'foo2', 'foo3']

            response = yield from c.kv.delete('foo2')
            assert response is True
            index, data = yield from c.kv.get('foo', recurse=True)
            assert [x['Key'] for x in data] == ['foo1', 'foo3']
            response = yield from c.kv.delete('foo', recurse=True)
            assert response is True
            index, data = yield from c.kv.get('foo', recurse=True)
            assert data is None
            c.close()

        loop.run_until_complete(main())

    def test_kv_subscribe(self, loop, consul_port):
        c = consul.aio.Consul(port=consul_port, loop=loop)

        @asyncio.coroutine
        def get():
            fut = asyncio.async(put(), loop=loop)
            index, data = yield from c.kv.get('foo')
            assert data is None
            index, data = yield from c.kv.get('foo', index=index)
            assert data['Value'] == six.b('bar')
            yield from fut
            c.close()

        @asyncio.coroutine
        def put():
            yield from asyncio.sleep(1.0/100, loop=loop)
            response = yield from c.kv.put('foo', 'bar')
            assert response is True

        loop.run_until_complete(get())

    def test_transaction(self, loop, consul_port):
        @asyncio.coroutine
        def main():
            c = consul.aio.Consul(port=consul_port, loop=loop)
            value = base64.b64encode(b"1").decode("utf8")
            d = {"KV": {"Verb": "set", "Key": "asdf", "Value": value}}
            r = yield from c.txn.put([d])
            assert r["Errors"] is None

            d = {"KV": {"Verb": "get", "Key": "asdf"}}
            r = yield from c.txn.put([d])
            assert r["Results"][0]["KV"]["Value"] == value
            c.close()
        loop.run_until_complete(main())

    def test_agent_services(self, loop, consul_port):
        @asyncio.coroutine
        def main():
            c = consul.aio.Consul(port=consul_port, loop=loop)
            services = yield from c.agent.services()
            assert services == {}
            response = yield from c.agent.service.register('foo')
            assert response is True
            services = yield from c.agent.services()
            assert services == {
                'foo': {
                    'Port': 0,
                    'ID': 'foo',
                    'CreateIndex': 0,
                    'ModifyIndex': 0,
                    'EnableTagOverride': False,
                    'Service': 'foo',
                    'Tags': [],
                    'Address': ''}, }
            response = yield from c.agent.service.deregister('foo')
            assert response is True
            services = yield from c.agent.services()
            assert services == {}
            c.close()

        loop.run_until_complete(main())

    def test_catalog(self, loop, consul_port):
        c = consul.aio.Consul(port=consul_port, loop=loop)

        @asyncio.coroutine
        def nodes():
            fut = asyncio.async(register(), loop=loop)
            index, nodes = yield from c.catalog.nodes()
            assert len(nodes) == 1
            current = nodes[0]

            index, nodes = yield from c.catalog.nodes(index=index)
            nodes.remove(current)
            assert [x['Node'] for x in nodes] == ['n1']

            index, nodes = yield from c.catalog.nodes(index=index)
            nodes.remove(current)
            assert [x['Node'] for x in nodes] == []
            yield from fut
            c.close()

        @asyncio.coroutine
        def register():
            yield from asyncio.sleep(1.0/100, loop=loop)
            response = yield from c.catalog.register('n1', '10.1.10.11')
            assert response is True
            yield from asyncio.sleep(50/1000.0, loop=loop)
            response = yield from c.catalog.deregister('n1')
            assert response is True

        loop.run_until_complete(nodes())

    def test_session(self, loop, consul_port):
        c = consul.aio.Consul(port=consul_port, loop=loop)

        @asyncio.coroutine
        def monitor():
            fut = asyncio.async(register(), loop=loop)
            index, services = yield from c.session.list()
            assert services == []
            yield from asyncio.sleep(20/1000.0, loop=loop)

            index, services = yield from c.session.list(index=index)
            assert len(services)

            index, services = yield from c.session.list(index=index)
            assert services == []
            yield from fut
            c.close()

        @asyncio.coroutine
        def register():
            yield from asyncio.sleep(1.0/100, loop=loop)
            session_id = yield from c.session.create()
            yield from asyncio.sleep(50/1000.0, loop=loop)
            response = yield from c.session.destroy(session_id)
            assert response is True

        loop.run_until_complete(monitor())

    def test_acl(self, loop, acl_consul):
        @asyncio.coroutine
        def main():
            c = consul.aio.Consul(
                port=acl_consul.port, token=acl_consul.token, loop=loop)

            rules = """
                key "" {
                    policy = "read"
                }
                key "private/" {
                    policy = "deny"
                }
            """
            token = yield from c.acl.create(rules=rules)

            try:
                yield from c.acl.list(token=token)
            except consul.ACLPermissionDenied:
                raised = True
            assert raised

            destroyed = yield from c.acl.destroy(token)
            assert destroyed is True
            c.close()

        loop.run_until_complete(main())

    @pytest.mark.skipif(sys.version_info < (3, 4, 1),
                        reason="Python <3.4.1 doesnt support __del__ calls "
                               "from GC")
    def test_httpclient__del__method(self, loop, consul_port, recwarn):

        @asyncio.coroutine
        def main():
            c = consul.aio.Consul(port=consul_port, loop=loop)
            _, _ = yield from c.kv.get('foo')
            del c
            import gc
            # run gc to ensure c is collected
            gc.collect()
            w = recwarn.pop(ResourceWarning)
            assert issubclass(w.category, ResourceWarning)

        loop.run_until_complete(main())
