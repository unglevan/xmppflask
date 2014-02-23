# -*- coding: utf-8 -*-
"""
    XmppFlask Tests
    ~~~~~~~~~~~~~~~

    Test XmppFlask Request/Response wrappers.

    :copyright: (c) 2012 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

from xmppflask import JID
from xmppflask.tests.helpers import unittest
from xmppflask.wrappers import Request, Response


class RequestTestCase(unittest.TestCase):

    def test_request_jid(self):
        jid = JID('user@domain/resource')
        req = Request({'xmpp.jid': jid})
        self.assertTrue(jid is req.jid)

    def test_request_app_jid(self):
        jid = JID('user@domain/resource')
        req = Request({'app.jid': jid})
        self.assertTrue(jid is req.app_jid)

    def test_request_body(self):
        req = Request({'xmpp.body': 'message'})
        self.assertEqual(req.body, 'message')

    def test_request_xml(self):
        req = Request({'xmpp.xml': '<message/>'})
        self.assertEqual(req.xml, '<message/>')

    def test_request_event(self):
        req = Request({'xmpp.stanza': 'presence'})
        self.assertEqual(req.event, 'presence')

    def test_request_type(self):
        req = Request({'xmpp.stanza_type': 'available'})
        self.assertEqual(req.type, 'available')

    def test_request_id(self):
        req = Request({'xmpp.id': 'xmppflask12345'})
        self.assertEqual(req.id, 'xmppflask12345')

    def test_request_username(self):
        jid = JID('user@domain/resource')
        req = Request({'xmpp.jid': jid, 'xmpp.stanza_type': 'chat'})
        self.assertEqual(req.username, 'user')

    def test_request_username_groupchat(self):
        jid = JID('user@domain/resource')
        req = Request({'xmpp.jid': jid, 'xmpp.stanza_type': 'groupchat'})
        self.assertEqual(req.username, 'resource')


class ResponseTestCase(unittest.TestCase):

    def test_init_by_string(self):
        resp = Response('foo')
        self.assertEqual(list(resp), ['foo'])

    def test_init_by_iterable(self):
        resp = Response([1, 2, 3])
        self.assertEqual(list(resp), [1, 2, 3])

        resp = Response(('foo', 'bar', 'baz'))
        self.assertEqual(list(resp), ['foo', 'bar', 'baz'])

        resp = Response(xrange(2))
        self.assertEqual(list(resp), [0, 1])

        resp = Response({'foo': 'bar'})
        self.assertEqual(list(resp), ['foo'])

    def test_single_pair_response(self):
        resp = Response(('foo', 'bar'))
        self.assertEqual(list(resp), [('foo', 'bar')])

    def test_init_by_other(self):
        class Foo(object):
            def __str__(self):
                return 'foo'

        resp = Response(42)
        self.assertEqual(list(resp), ['42'])

        resp = Response(Foo())
        self.assertEqual(list(resp), ['foo'])

    def test_not_iterable_twice(self):
        resp = Response('foo')
        self.assertEqual(list(resp), ['foo'])
        self.assertEqual(list(resp), [])

    def test_concat_responses(self):
        orig_resp = Response('foo')
        resp = orig_resp(Response('bar'))
        self.assertTrue(orig_resp is resp)

        resp = resp(Response('baz'))

        self.assertEqual(list(resp), ['foo', 'bar', 'baz'])

    def test_lazy_iterator(self):
        gen = (i for i in range(3))
        resp = Response(42)(gen)

        self.assertEqual(gen.next(), 0)
        self.assertEqual(resp.next(), '42')
        self.assertEqual(gen.next(), 1)
        self.assertEqual(resp.next(), 2)
        self.assertRaises(StopIteration, gen.next)

    def test_coroutine(self):
        def gen():
             ok = yield 'foo'
             assert ok
             ok = yield 'bar'
             assert ok
        resp = Response(gen())
        self.assertEqual(resp.send(None), 'foo')
        self.assertEqual(resp.send(True), 'bar')
        self.assertRaises(StopIteration, resp.send, True)
