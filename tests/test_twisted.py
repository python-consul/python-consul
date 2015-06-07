"""
Tests for the twisted integration.

Run these by  simply running:
    trial tests/test_twisted.py
"""
import struct
# import six

from consul.twisted import Consul
from twisted.internet import defer
from twisted.trial import unittest
from treq._utils import _global_pool as pool


class TwistedConsul(unittest.TestCase):

    """Tests for the Twisted HTTPClient based Consul."""

    def setUp(self):
        """Create the consul instance."""
        self.c = Consul()

    def tearDown(self):
        """https://github.com/dreid/treq/issues/86."""
        pool[0].closeCachedConnections()

    @defer.inlineCallbacks
    def test_kv(self):
        """Test simple key value data."""
        yield self.c.kv.delete('foo')
        index, data = yield self.c.kv.get('foo')
        self.assertEqual(data, None)
        response = yield self.c.kv.put('foo', 'bar')
        self.assertTrue(response)
        index, data = yield self.c.kv.get('foo')
        self.assertEqual(data['Value'], "bar")

    @defer.inlineCallbacks
    def test_kv_binary(self):
        """Test binary key value data."""
        yield self.c.kv.delete('foo')
        yield self.c.kv.put('foo', struct.pack('i', 1000))
        index, data = yield self.c.kv.get('foo')
        self.assertEqual(struct.unpack('i', data['Value']), (1000,))

    @defer.inlineCallbacks
    def test_kv_missing(self):
        """Test when a value is missing."""
        yield self.c.kv.delete('foo')
        yield self.c.kv.put('index', 'bump')
        index, data = yield self.c.kv.get('foo')
        self.assertEqual(data, None)
        # Line below seems to block.
        # index, data = yield self.c.kv.get('foo', index=index)
        # self.assertEqual(data['Value'], six.b('bar'))

    @defer.inlineCallbacks
    def test_agent_services(self):
        """Test getting services from the agent."""
        services = yield self.c.agent.services()
        del services['consul']
        self.assertEqual(services, {})
