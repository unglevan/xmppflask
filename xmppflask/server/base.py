# -*- coding: utf-8 -*-
"""
    xmppflask.server.base
    ~~~~~~~~~~~~~~~~~~~~~

    Base XMPPWSGI server interface.

    :copyright: (c) 2014 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

import inspect
import time
import sys
from abc import ABCMeta, abstractmethod
from collections import Mapping, OrderedDict
from pprint import pformat
from .caps import Capability, CapabilityNotFound


class XmppWsgiServer(object):
    """Base abstract XMPPWSGI server."""

    __metaclass__ = ABCMeta

    #: Proxy to XMPP module.
    module = None
    #: Proxy to active XMPP client instance.
    xmpp = None

    message_class = None
    presence_class = None
    iq_class = None

    capability_class = Capability

    def __init__(self, app):
        self.app = app
        self.app_ctx = app.app_context()
        self.base_environ = self.create_environ()
        self.caps = OrderedDict()
        self.commands = {}

    @abstractmethod
    def connect(self, jid, pwd, use_tls=True, use_ssl=False):
        """Should establish connection for specified credentials."""
        raise NotImplementedError

    @abstractmethod
    def session_start(self):
        """Should be called after successful connection and authentication."""
        self.register_capability('std')  # force to have standard capability
        self.register_capabilities()
        self.check_app_requirements()

    @abstractmethod
    def serve_forever(self):
        """Should implement infinity loop if needed."""
        raise NotImplementedError

    def lookup_capability(self, name):
        """Lookups capability by name for current XMPPWSGI server.

        :param name: Capability name
        :type name: str

        :returns: Capability class or None if missed
        :rtype: :class:~`xmppflask.server.Capability`
        """
        for cap in self.capability_class.__subclasses__():
            if cap.name == name:
                return cap

    def register_capabilities(self):
        """Register all capabilities that server is able to have."""
        for cap in self.capability_class.__subclasses__():
            self.register_capability(cap)

    def register_capability(self, obj):
        """Registers server capability"""
        if isinstance(obj, basestring):
            capname = obj
            if capname in self.caps:
                return
            capcls = self.lookup_capability(capname)
            if capcls is None:
                raise CapabilityNotFound(capname)
            return self.register_capability(capcls)
        elif issubclass(obj, self.capability_class):
            capcls = obj
            if capcls.name in self.caps:
                return
            cap = capcls(self)
        elif isinstance(obj, self.capability_class):
            cap = obj
            if cap.name in self.caps:
                return
        else:
            raise TypeError(repr(obj))
        self.app.logger.info('Initializing capability %s', cap.name)
        self.caps[cap.name] = cap
        for name, obj in inspect.getmembers(cap):
            if name.startswith('cmd_') and inspect.ismethod(obj):
                self.commands[name.split('cmd_')[-1]] = obj

    def check_app_requirements(self):
        """Verifies, that XmppWsgi server fulfills application requirements"""
        for expected in self.app.required_capabilities:
            if expected not in self.caps:
                raise CapabilityNotFound(expected)

    @staticmethod
    def create_environ():
        """Return base environ dict object with all known fields."""
        return {
            #: XmppFlask app JID
            'app.jid': None,
            #: Used protocol: tls, ssl or None
            'app.protocol': None,
            #: Stanza ID
            'xmpp.id': None,
            #: Sender JID
            'xmpp.jid': None,
            #: Stanza data as unicode string: message body, status message etc.
            'xmpp.body': None,
            #: Raw xml stanza as unicode string
            'xmpp.xml': None,
            #: Stanza class: message, presence, iq
            'xmpp.stanza': None,
            #: Stanza type: chat, groupchat, available etc.
            'xmpp.stanza_type': None,
            #: Presence stanza show: chat, dnd, away etc.
            'xmpp.status': None,
            #: Presence priority
            'xmpp.priority': None,

            #: Stanza UTC timestamp in ms
            'xmpp.timestamp': 0,
            #: Stanza delay in ms
            'xmpp.delay': 0,

            #: WSGI-like vars
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'xmpp',
            'wsgi.input': sys.stdin,
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
        }

    def setup_environ(self, stanza):
        """Creates new XMPPWSGI environ for current request.

        :param stanza: XMPP stanza as base for environ data.

        :return: XMPPWSGI environ
        :rtype: dict
        """
        if isinstance(stanza, self.message_class):
            stanza_cls = u'message'
        elif isinstance(stanza, self.presence_class):
            stanza_cls = u'presence'
        elif isinstance(stanza, self.iq_class):
            stanza_cls = u'iq'
        else:
            stanza_cls = None

        environ = self.base_environ.copy()
        environ['xmpp.stanza'] = stanza_cls
        environ['xmpp.timestamp'] = int(time.mktime(time.gmtime()))

        for cap in self.caps.values():
            cap.update_environ(environ, stanza)

        return environ

    def handle(self, stanza):
        """Handles XMPP stanza."""
        environ = self.setup_environ(stanza)
        # we don't want handle our own stanzas like presence
        if environ['app.jid'] == environ['xmpp.jid']:
            return
        # skip empty messages
        if environ['xmpp.stanza'] == 'message' and not environ['xmpp.body']:
            return
        self.app.logger.debug(pformat(environ))
        self.xmppwsgi_app(environ, [])

    def xmppwsgi_app(self, environ, notification_queue=None):
        """Calls bounded XMPPWSGI app with request-related environ."""
        with self.app_ctx:
            with self.app.request_context(environ):
                response = self.app(environ, notification_queue)
                self.dispatch_app_response(environ, response)
                self.dispatch_notification_queue(notification_queue)

    def dispatch_app_response(self, environ, response):
        """Response object dispatcher."""
        rv = None
        while True:
            try:
                item = response.send(rv)
            except StopIteration:
                break
            else:
                if isinstance(item, basestring):
                    cmd, payload = 'message', {'body': item}
                else:
                    cmd, payload = item
                    if isinstance(payload, basestring):
                        payload = {'body': payload}
                func = self.commands.get(cmd)
                if func is None:
                    raise ValueError('unknown command %r' % cmd)
                if not isinstance(payload, Mapping):
                    raise TypeError("command's payload should implement"
                                    " Mapping interface, got: %r"
                                    % type(payload))
                rv = func(environ, payload)

    def dispatch_notification_queue(self, queue):
        if not queue:
            return
        for jid, resp in queue:
            self.dispatch_app_response({'xmpp.jid': jid},
                                       self.app.response_class(resp))
