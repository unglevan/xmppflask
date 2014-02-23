# -*- coding: utf-8 -*-
"""
    XmppFlask Tests
    ~~~~~~~~~~~~~~~

    Test XmppFlask sessions.

    :copyright: (c) 2012 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

from xmppflask.tests.helpers import unittest
import xmppflask


class MemorySessionTestCase(unittest.TestCase):

    def setUp(self):
        from xmppflask.sessions import MemorySessionInterface

        self.app = xmppflask.XmppFlask(__name__)
        self.app.session_interface = MemorySessionInterface()

    def test_session_basic(self):
        """Basic test about Session initialization."""
        environ = {'xmpp.body': 'ping', 'xmpp.jid': 'k.bx@ya.ru'}

        @self.app.route(u'ping')
        def ping():
            from xmppflask.globals import session

            if 'times_pinged' not in session:
                session['times_pinged'] = 0
            session['times_pinged'] += 1
            return u'pong'

        self.app(environ)

        session = self.app.session_interface.storage[environ['xmpp.jid']]
        self.assertEquals(session['times_pinged'], 1)

    def test_session_should_keep_values(self):
        """Session should keep stored values for whole his lifespan."""
        environ = {'xmpp.body': 'ping', 'xmpp.jid': 'k.bx@ya.ru'}

        @self.app.route(u'ping')
        def ping():
            from xmppflask.globals import session

            if 'times_pinged' not in session:
                session['times_pinged'] = 0
            session['times_pinged'] += 1
            return u'pong'

        self.app(environ)
        self.app(environ)
        self.app(environ)

        session = self.app.session_interface.storage[environ['xmpp.jid']]
        self.assertEquals(session['times_pinged'], 3)

    def test_sessionless_workflow(self):
        """Test to be sure, that nullified sessions do not break anything."""
        environ = {'xmpp.body': 'PING', 'xmpp.jid': 'k.bx@ya.ru'}
        app = xmppflask.XmppFlask(__name__)

        @app.route(u'PING')
        def ping():
            return u'PONG'

        rv = app(environ)
        rv = app(environ)
        self.assertEquals(list(rv), ['PONG'])

    def test_session_expires(self):
        environ = {'xmpp.body': 'ping', 'xmpp.jid': 'k.bx@ya.ru'}

        @self.app.route(u'ping')
        def ping():
            from xmppflask.globals import session

            if 'times_pinged' not in session:
                session['times_pinged'] = 0
            session['times_pinged'] += 1
            return u'pong'

        self.app(environ)

        session = self.app.session_interface.storage[environ['xmpp.jid']]
        session._timestamp = 1  # tweak last update timestamp

        self.app(environ)

        # session was expired and all his data should be erased
        self.assertEquals(session['times_pinged'], 1)
