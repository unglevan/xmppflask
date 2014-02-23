# -*- coding: utf-8 -*-
"""
    XmppFlask Tests
    ~~~~~~~~~~~~~~~

    Test XmppFlask XMPPWSGI server.

    :copyright: (c) 2012 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

import sys
import time
import mock
from xmppflask.tests.helpers import unittest
from xmppflask import XmppFlask
from xmppflask.server import XmppWsgiServer, Capability, CapabilityNotFound


class TestServerCapability(Capability):
    pass


class TestStanza(object):
    pass


class Message(TestStanza):
    pass


class Presence(TestStanza):
    pass


class Iq(TestStanza):
    pass


class TestXmppWsgiServer(XmppWsgiServer):

    capability_class = TestServerCapability
    message_class = Message
    presence_class = Presence
    iq_class = Iq
    module = mock.Mock()
    xmpp = mock.Mock()

    def connect(self, jid, pwd, use_tls=True, use_ssl=False):
        pass

    def session_start(self):
        super(TestXmppWsgiServer, self).session_start()

    def serve_forever(self):
        pass


class XmppWsgiServerTestCase(unittest.TestCase):

    def setUp(self):
        app = XmppFlask('xmppflask.test')
        self.server = TestXmppWsgiServer(app)

    def test_create_environ(self):
        environ = self.server.create_environ()
        self.assertTrue('app.jid' in environ)
        self.assertTrue('app.protocol' in environ)
        self.assertTrue('xmpp.id' in environ)
        self.assertTrue('xmpp.jid' in environ)
        self.assertTrue('xmpp.body' in environ)
        self.assertTrue('xmpp.xml' in environ)
        self.assertTrue('xmpp.stanza' in environ)
        self.assertTrue('xmpp.stanza_type' in environ)
        self.assertTrue('xmpp.status' in environ)
        self.assertTrue('xmpp.priority' in environ)
        self.assertTrue('xmpp.timestamp' in environ)
        self.assertTrue('xmpp.delay' in environ)

        self.assertEqual(environ['wsgi.version'], (1, 0))
        self.assertEqual(environ['wsgi.url_scheme'], 'xmpp')
        self.assertTrue(environ['wsgi.input'] is sys.stdin)
        self.assertTrue(environ['wsgi.errors'] is sys.stderr)
        self.assertEqual(environ['wsgi.multiprocess'], False)
        self.assertEqual(environ['wsgi.multithread'], False)
        self.assertEqual(environ['wsgi.run_once'], False)

    def test_setup_environ_from_message(self):
        environ = self.server.setup_environ(Message())
        self.assertEqual(environ['xmpp.stanza'], 'message')

    def test_setup_environ_from_presence(self):
        environ = self.server.setup_environ(Presence())
        self.assertEqual(environ['xmpp.stanza'], 'presence')

    def test_setup_environ_from_iq(self):
        environ = self.server.setup_environ(Iq())
        self.assertEqual(environ['xmpp.stanza'], 'iq')

    def test_setup_environ_from_else(self):
        environ = self.server.setup_environ(object())
        self.assertEqual(environ['xmpp.stanza'], None)

    def test_setup_environ_creates_copy_of_base_one(self):
        self.server.base_environ['app.jid'] = 'k.bx@ya.ru'
        environ = self.server.setup_environ(Message())
        self.assertEqual(environ['app.jid'],
                         self.server.base_environ['app.jid'])
        self.assertFalse(self.server.base_environ is environ)

    def test_setup_environ_sets_utc_timestamp(self):
        environ = self.server.setup_environ(Message())
        self.assertNotEqual(environ['xmpp.timestamp'], 0)

        trim = lambda n: int(n) / 100 * 100  # lets compare approximate values
        ts = trim(environ['xmpp.timestamp'])
        utcts = trim(time.mktime(time.gmtime()))
        localts = trim(time.time())

        self.assertEqual(ts, utcts)
        self.assertNotEqual(ts, localts)

    def test_register_capability(self):
        class Feature(TestServerCapability):
            name = 'very useful'

        self.server.register_capability(Feature)
        self.assertTrue('very useful' in self.server.caps)
        self.assertTrue(isinstance(self.server.caps['very useful'], Feature))

    def test_register_capability_by_name(self):
        class VeryFeature(TestServerCapability):
            name = 'so useful'

        self.server.register_capability('so useful')
        self.assertTrue('so useful' in self.server.caps)
        self.assertTrue(isinstance(self.server.caps['so useful'],
                                   VeryFeature))

    def test_register_capability_by_instance(self):
        class Feature(TestServerCapability):
            name = 'very useful'

        self.server.register_capability(Feature(mock.Mock()))
        self.assertTrue('very useful' in self.server.caps)
        self.assertTrue(isinstance(self.server.caps['very useful'], Feature))

    def test_register_unknown_capability(self):
        self.assertRaises(CapabilityNotFound,
                          self.server.register_capability, 'foo')

    def test_register_weird_capability(self):
        self.assertRaises(TypeError,
                          self.server.register_capability, object())

    def test_dont_register_same_capability_twice(self):
        class Feature(TestServerCapability):
            name = 'very useful'

            instances = 0

            def __init__(self, *args, **kwargs):
                super(Feature, self).__init__(*args, **kwargs)
                self.instances += 1
                assert self.instances < 2

        self.server.register_capability('very useful')
        self.server.register_capability('very useful')
        self.server.register_capability(Feature)
        self.server.register_capability(Feature)
        self.server.register_capability(Feature)
        self.assertTrue('very useful' in self.server.caps)
        self.assertTrue(isinstance(self.server.caps['very useful'], Feature))

    def test_register_capability_type_error(self):
        self.assertRaises(TypeError, self.server.register_capability, None)

    def test_lookup_capability(self):
        class Feature(TestServerCapability):
            name = 'very useful'

        assert self.server.lookup_capability('very useful') is Feature

    def test_look_capability_missing(self):
        assert self.server.lookup_capability('not very useful') is None

    def test_server_fulfill_app_requirements(self):
        class Feature(TestServerCapability):
            name = 'feature'

        self.server.app.required_capabilities = ['feature']
        self.server.register_capability(Feature)
        self.server.check_app_requirements()

    def test_app_requirements_not_satisfied(self):
        self.server.app.required_capabilities = ['feature']
        self.assertRaises(CapabilityNotFound,
                          self.server.check_app_requirements)

    def test_capabilities_brings_commands(self):
        class SoFeature(TestServerCapability):
            name = 'wow'

            def cmd_bar(self):
                pass

        self.server.register_capability(SoFeature(mock.Mock()))
        self.assertTrue('bar' in self.server.commands)

    def test_capabilities_updates_environ(self):
        class SoFeature(TestServerCapability):
            name = 'very userful'

            def update_environ(self, environ, stanza):
                environ['test'] = 'passed'

        self.server.register_capability(SoFeature(mock.Mock()))
        environ = self.server.setup_environ(Message())
        self.assertEqual(environ['test'], 'passed')

    def test_dispatch_app_response(self):
        def message(environ, payload):
            self.assertEqual('ping', payload['body'])

        self.server.commands['message'] = message
        environ = self.server.create_environ()
        response = self.server.app.response_class('ping')
        self.server.dispatch_app_response(environ, response)

    def test_dispatch_app_response_unknown_command(self):
        environ = self.server.create_environ()
        response = self.server.app.response_class('ping')
        self.assertRaises(
            ValueError,
            self.server.dispatch_app_response,
            environ, response
        )

    def test_dispatch_weird_response(self):
        environ = {'xmpp.jid': 'foo@bar'}
        resp = self.server.app.response_class([('foo', 'boo')])

        self.assertRaises(ValueError,
                          self.server.dispatch_app_response, environ, resp)

    def test_dispatch_coroutine(self):
        def ping():
            assert (yield 'presence', {'type': 'foo'})
            assert (yield 'presence', {'type': 'bar'})
            assert (yield 'presence', {'type': 'baz'})
            assert (yield 'PONG!')

        def message(environ, payload):
            queue.append(('message', payload))
            return True

        def presence(environ, payload):
            queue.append(('presence', payload))
            return True

        queue = []
        environ = {'xmpp.jid': 'foo@bar'}
        self.server.commands['message'] = message
        self.server.commands['presence'] = presence
        resp = self.server.app.response_class(ping())

        self.server.dispatch_app_response(environ, resp)

        self.assertEqual(len(queue), 4)

        seq = ['foo', 'bar', 'baz']
        for idx, type_ in enumerate(seq):
            cmd, payload = queue[idx]
            self.assertEqual(cmd, 'presence')
            self.assertEqual(payload['type'], type_)

        cmd, payload = queue[-1]
        self.assertEqual(cmd, 'message')
        self.assertEqual(payload['body'], 'PONG!')

    def test_preserve_req_ctx_for_generators(self):
        app = self.server.app

        @app.route('reqctx')
        def reqctx():
            from xmppflask import session
            yield 'reqctx'
            session.get('somevar')

        def message(environ, payload):
            self.assertEqual('reqctx', payload['body'])

        self.server.commands['message'] = message

        environ = {'xmpp.jid': 'k.bx@ya.ru', 'xmpp.body': 'reqctx'}
        self.server.xmppwsgi_app(environ, [])

    def test_preserve_app_ctx_for_generators(self):
        app = self.server.app

        @app.route('appctx')
        def appctx():
            from xmppflask import g
            yield 'appctx'
            g.get('somevar')

        def message(environ, payload):
            self.assertEqual('appctx', payload['body'])

        self.server.commands['message'] = message

        environ = {'xmpp.jid': 'k.bx@ya.ru', 'xmpp.body': 'appctx'}
        self.server.xmppwsgi_app(environ, [])

    def test_handle(self):
        class Feature(TestServerCapability):
            name = 'feature'

            def cmd_message(self, environ, payload):
                assert payload['body'] == 'pong'
                return True

            def update_environ(self, environ, stanza):
                environ['app.jid'] = 'k.bx@ya.ru'
                environ['xmpp.body'] = 'ping'
                environ['xmpp.jid'] = 'other@ya.ru'

        app = self.server.app

        @app.route('ping')
        def ping():
            return 'pong'

        self.server.register_capability(Feature)
        self.server.handle(Message())

    def test_handle_skip_stanza_from_self(self):
        class Feature(TestServerCapability):
            name = 'feature'

            def cmd_message(self, environ, payload):
                assert payload['body'] == 'pong'
                return True

            def update_environ(self, environ, stanza):
                environ['app.jid'] = 'k.bx@ya.ru'
                environ['xmpp.body'] = 'ping'
                environ['xmpp.jid'] = 'k.bx@ya.ru'

        app = self.server.app

        @app.route('ping')
        def ping():
            assert False

        self.server.register_capability(Feature)
        self.server.handle(Message())

    def test_handle_skip_empty_messages(self):
        class Feature(TestServerCapability):
            name = 'feature'

            def cmd_message(self, environ, payload):
                assert payload['body'] == 'pong'
                return True

            def update_environ(self, environ, stanza):
                environ['app.jid'] = 'k.bx@ya.ru'
                environ['xmpp.body'] = ''
                environ['xmpp.jid'] = 'other@ya.ru'

        app = self.server.app

        @app.route('ping')
        def ping():
            assert False

        self.server.register_capability(Feature)
        self.server.handle(Message())


if __name__ == '__main__':
    unittest.main()
