# -*- coding: utf-8 -*-
"""
    xmppflask.wrappers
    ~~~~~~~~~~~~~~~~~~

    Implement wrappers for request and response

    :copyright: (c) 2014 Kostyantyn Rybnikov <k.bx@ya.ru>
    :license: BSD
"""
from collections import Iterable, Iterator, Callable
from types import GeneratorType


class Request(object):

    #: if matching the route failed, this is the exception that will be
    #: raised / was raised as part of the request handling.  This is
    #: usually a :exc:`~xmppflask.exceptions.NotFound` exception or
    #: something similar.
    routing_exception = None

    #: the internal route rule that matched the request.
    route_rule = None
    view_args = None

    def __init__(self, environ):
        self.environ = environ

    @property
    def app_jid(self):
        """XmppFlask app JID"""
        return self.environ['app.jid']

    @property
    def id(self):
        """XMPP Stanza ID"""
        return self.environ['xmpp.id']

    @property
    def body(self):
        """Incoming message body, status message etc."""
        return self.environ['xmpp.body']

    @property
    def xml(self):
        """Raw stanza XML"""
        return self.environ['xmpp.xml']

    @property
    def event(self):
        """XMPP stanza kind: message, presence, iq"""
        return self.environ['xmpp.stanza']

    @property
    def jid(self):
        """Sender :class:~`xmppflask.JID` instance"""
        return self.environ['xmpp.jid']

    @property
    def type(self):
        """XMPP stanza type: chat, groupchat, available, etc."""
        return self.environ['xmpp.stanza_type']

    @property
    def username(self):
        """Sender username"""
        if self.type == 'groupchat':
            return self.jid.resource
        return self.jid.user

    @property
    def endpoint(self):
        """The endpoint that matched the request.  This in combination with
        :attr:`view_args` can be used to reconstruct the same or a
        modified route.  If an exception happened when matching, this will
        be `None`.
        """
        if self.route_rule is not None:
            return self.route_rule.endpoint

    @property
    def blueprint(self):
        """The name of the current blueprint"""
        if self.route_rule and '.' in self.route_rule.endpoint:
            return self.route_rule.endpoint.rsplit('.', 1)[0]


class Response(Iterator, Callable):
    """Response object which implements iterator interface."""

    def __init__(self, data):
        self._stack = []
        self._current = self._wrap(data)

    def __call__(self, other):
        self._stack.append(self._wrap(other))
        return self

    def __iter__(self):
        return self

    def _wrap(self, data):
        if not isinstance(data, GeneratorType):
            if isinstance(data, basestring):
                data = [data]
            elif data is None:
                data = []
            elif isinstance(data, (tuple, list)) and len(data) == 2:
                data = [data]
            elif not isinstance(data, Iterable):
                data = [str(data)]
            return (item for item in data)
        return data

    def next(self):
        return self.send(None)

    def send(self, value):
        try:
            return self._current.send(value)
        except StopIteration:
            if self._stack:
                self._current = self._stack.pop(0)
                return self.next()
            else:
                raise

    def throw(self, exc_type, exc_val=None, exc_tb=None):
        resp = self._current.throw(exc_type, exc_val, exc_tb)
        if resp is not None:
            return resp

    def close(self):
        self._current.close()
