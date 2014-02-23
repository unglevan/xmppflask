# -*- coding: utf-8 -*-
"""
    xmppflask.test.test_appctx
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests the application context.

    :copyright: (c) 2014 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

import xmppflask
from xmppflask.tests.helpers import unittest


class AppContextTestCase(unittest.TestCase):

    def test_request_context_means_app_context(self):
        app = xmppflask.XmppFlask(__name__)
        with app.request_context({'xmpp.jid': 'k.bx@ya.ru'}):
            self.assertEqual(xmppflask.current_app._get_current_object(), app)
        self.assertEqual(xmppflask._app_ctx_stack.top, None)

    def test_app_context_provides_current_app(self):
        app = xmppflask.XmppFlask(__name__)
        with app.app_context():
            self.assertEqual(xmppflask.current_app._get_current_object(), app)
        self.assertEqual(xmppflask._app_ctx_stack.top, None)

    def test_app_tearing_down(self):
        cleanup_stuff = []
        app = xmppflask.XmppFlask(__name__)
        @app.teardown_appcontext
        def cleanup(exception):
            cleanup_stuff.append(exception)

        with app.app_context():
            pass

        self.assertEqual(cleanup_stuff, [None])

    def test_custom_app_ctx_globals_class(self):
        class CustomRequestGlobals(object):
            def __init__(self):
                self.spam = 'eggs'
        app = xmppflask.XmppFlask(__name__)
        app.app_ctx_globals_class = CustomRequestGlobals
        with app.app_context():
            self.assertEqual(
                xmppflask.render_template_string('{{ g.spam }}'), 'eggs')

    def test_context_refcounts(self):
        called = []
        app = xmppflask.XmppFlask(__name__)
        @app.teardown_request
        def teardown_req(error=None):
            called.append('request')
        @app.teardown_appcontext
        def teardown_app(error=None):
            called.append('app')
        @app.route('ping')
        def ping():
            with xmppflask._app_ctx_stack.top:
                with xmppflask._request_ctx_stack.top:
                    pass
            return u'pong'
        environ = {'xmpp.body': 'ping', 'xmpp.jid': 'k.bx@ya.ru'}
        app(environ)
        self.assertEqual(called, ['request', 'app'])
