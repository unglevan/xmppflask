# -*- coding: utf-8 -*-
"""
    XmppFlask Tests
    ~~~~~~~~~~~~~~~

    Test XmppFlask itself.

    :copyright: (c) 2011 Kostyantyn Rybnikov <k.bx@ya.ru>
    :license: BSD
"""

import xmppflask
from xmppflask.tests.helpers import unittest


class BasicFunctionalityTestCase(unittest.TestCase):

    def test_xmppwsgi_simple(self):
        environ = {'xmpp.body': 'PING', 'xmpp.jid': 'k.bx@ya.ru'}
        app = xmppflask.XmppFlask(__name__)

        @app.route(u'PING')
        def ping():
            return u'PONG'

        rv = app(environ)
        self.assertEquals(list(rv), ['PONG'])

    def test_xmppwsgi_more_complex(self):
        environ = {'xmpp.body': 'PING 10 times', 'xmpp.jid': 'k.bx@ya.ru'}
        app = xmppflask.XmppFlask(__name__)

        @app.route(u'PING <int:times> times')
        def ping(times):
            return u'PONG %s times' % times

        rv = app(environ)
        self.assertEquals(list(rv), ['PONG 10 times'])

    def test_template_rendering(self):
        from xmppflask import render_template

        environ = {'xmpp.jid': 'k.bx@ya.ru'}
        app = xmppflask.XmppFlask(__name__, template_folder='../templates')

        @app.route(u'ping')
        def ping():
            return render_template('ping.html')

        @app.route(u'ping <user>')
        def ping_user(user):
            return render_template('ping.html', user=user)

        @app.route(u'template_not_found')
        def template_not_found():
            return render_template('template_not_found.html')

        environ['xmpp.body'] = 'ping'
        rv = app(environ)
        self.assertEquals(list(rv), ['pong'])

        environ['xmpp.body'] = 'ping k_bx'
        rv = app(environ)
        self.assertEquals(list(rv), ['pong from k_bx'])

    def test_template_rendering_with_message_for(self):
        from xmppflask import render_template

        app = xmppflask.XmppFlask(__name__, template_folder='../templates')

        @app.route(u'message_for_test')
        def message_for_test():
            return render_template('message_for_test.html')

        environ = {'xmpp.jid': 'k.bx@ya.ru'}

        environ['xmpp.body'] = 'message_for_test'
        rv = app(environ)
        self.assertEquals(u''.join(rv), 'message_for_test')

    def test_context_simple(self):
        app = xmppflask.XmppFlask(__name__)

        @app.route(u'ping')
        def message_for_test():
            from xmppflask import g

            g.some_val = 'some val'
            return u'pong %s' % g.some_val

        environ = {'xmpp.jid': 'k.bx@ya.ru'}

        notification_queue = []
        environ['xmpp.body'] = 'ping'
        rv = app(environ, notification_queue)
        self.assertEquals(u''.join(rv), 'pong some val')

    def test_notification(self):
        from xmppflask.notification import notify

        app = xmppflask.XmppFlask(__name__)

        @app.route(u'ping')
        def message_for_test():
            notify('kost-bebix@ya.ru', 'ping route')
            return u'pong'

        environ = {'xmpp.jid': 'k.bx@ya.ru'}

        notification_queue = []
        environ['xmpp.body'] = 'ping'
        rv = app(environ, notification_queue)
        self.assertEquals(u''.join(rv), 'pong')
        self.assertEquals(notification_queue,
                          [('kost-bebix@ya.ru', 'ping route')])

    def test_before_request(self):
        from xmppflask import g

        app = xmppflask.XmppFlask(__name__)

        must_be_changed = {'status': 'not changed'}

        @app.before_request
        def before_request():
            g.db = 'db obj'

        @app.teardown_request
        def teardown_request(exception):
            must_be_changed['status'] = 'changed'

        @app.route(u'ping')
        def message_for_test():
            self.assertEquals(g.db, 'db obj')
            return u'pong'

        environ = {'xmpp.jid': 'k.bx@ya.ru'}

        environ['xmpp.body'] = 'ping'
        rv = app(environ)
        self.assertEquals(u''.join(rv), 'pong')
        self.assertEquals(must_be_changed['status'], 'changed')

    def test_static_url_path(self):
        app = xmppflask.XmppFlask(__name__)

        @app.route(u'ping')
        def ping():
            return u'pong'

        environ = {'xmpp.jid': 'k.bx@ya.ru'}

        environ['xmpp.body'] = 'ping'
        self.assertEquals(app.static_url_path,
                          None)

    def test_user_exception(self):
        class TestException(Exception): pass

        app = xmppflask.XmppFlask(__name__)
        app.debug = True

        @app.route(u'ping')
        def ping():
            raise TestException('wrong!')

        environ = {'xmpp.jid': 'k.bx@ya.ru'}

        environ['xmpp.body'] = 'ping'
        self.assertRaises(TestException, lambda: app(environ))

    def test_handle_presences(self):
        app = xmppflask.XmppFlask(__name__)

        @app.route_presence()
        def presence():
            return 'got it'

        environ = {'xmpp.jid': 'k.bx@ya.ru', 'xmpp.stanza_type': 'presence'}

        rv = app(environ)
        self.assertEquals(u''.join(rv), 'got it')

    def test_handle_presences_from_specific_domain(self):
        app = xmppflask.XmppFlask(__name__)

        @app.route_presence(from_jid='.*@ya.ru', type='available')
        def presence():
            return 'welcome back, %s!' % environ['xmpp.jid']

        environ = {'xmpp.jid': xmppflask.JID('k.bx@ya.ru'),
                   'xmpp.stanza': 'presence',
                   'xmpp.stanza_type': 'available'}

        rv = app(environ)
        self.assertEquals(u''.join(rv),
                          'welcome back, %s!' % environ['xmpp.jid'])

    def test_presence_mismatch_doesnt_return_message_not_understood_resp(self):
        app = xmppflask.XmppFlask(__name__)

        @app.route_presence(from_jid='.*@ya.ru', type='available')
        def presence():
            return 'welcome back, %s!' % environ['xmpp.jid']

        environ = {'xmpp.jid': 'foo@bar',
                   'xmpp.stanza': 'presence',
                   'xmpp.body': '',
                   'xmpp.stanza_type': 'available'}

        rv = app(environ)
        self.assertEquals(u''.join(rv), '')
