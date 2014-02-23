# -*- coding: utf-8 -*-
"""
    xmppflask.ctx
    ~~~~~~~~~~~~~

    Objects required to keep the context.

    :copyright: (c) 2014 Kostyantyn Rybnikov <k.bx@ya.ru>
    :license: BSD
"""

import sys
from .globals import _request_ctx_stack, _app_ctx_stack
from .exceptions import XMPPException


class _AppCtxGlobals(object):

    def get(self, name, default=None):
        return self.__dict__.get(name, default)

    def __contains__(self, item):
        return item in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)

    def __repr__(self):
        top = _app_ctx_stack.top
        if top is not None:
            return '<xmppflask.g of %r>' % top.app.name
        return object.__repr__(self)


class AppContext(object):

    def __init__(self, app):
        self.app = app
        self.g = app.app_ctx_globals_class()

        # Like request context, app contexts can be pushed multiple times
        # but there a basic "refcount" is enough to track them.
        self._refcnt = 0

    def push(self):
        """Binds the app context to the current context."""
        self._refcnt += 1
        _app_ctx_stack.push(self)

    def pop(self, exc=None):
        """Pops the app context."""
        self._refcnt -= 1
        if self._refcnt <= 0:
            if exc is None:
                exc = sys.exc_info()[1]
            self.app.do_teardown_appcontext(exc)
        rv = _app_ctx_stack.pop()
        assert rv is self, 'Popped wrong app context.  (%r instead of %r)' \
            % (rv, self)

    def __enter__(self):
        self.push()
        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop(exc_value)


class RequestContext(object):
    def __init__(self, app, environ):
        self.app = app
        self.request = app.request_class(environ)
        self.route_adapter = app.create_route_adapter(self.request)
        self.session = None

        # Request contexts can be pushed multiple times and interleaved with
        # other request contexts.  Now only if the last level is popped we
        # get rid of them.  Additionally if an application context is missing
        # one is created implicitly so for each level we add this information
        self._implicit_app_ctx_stack = []

        self.match_request()

    def _get_g(self):
        return _app_ctx_stack.top.g
    def _set_g(self, value):
        _app_ctx_stack.top.g = value
    g = property(_get_g, _set_g)
    del _get_g, _set_g

    def match_request(self):
        try:
            route_rule, self.request.view_args = \
                self.route_adapter.match(return_rule=True)
            self.request.route_rule = route_rule
        except XMPPException, e:
            self.request.routing_exception = e

    def push(self):
        # Before we push the request context we have to ensure that there
        # is an application context.
        app_ctx = _app_ctx_stack.top
        if app_ctx is None or app_ctx.app != self.app:
            app_ctx = self.app.app_context()
            app_ctx.push()
            self._implicit_app_ctx_stack.append(app_ctx)
        else:
            self._implicit_app_ctx_stack.append(None)

        _request_ctx_stack.push(self)

        self.session = self.app.open_session(self.request)
        if self.session is None:
            self.session = self.app.make_null_session()

    def pop(self, exc=None):
        app_ctx = self._implicit_app_ctx_stack.pop()
        if not self._implicit_app_ctx_stack:
            if exc is None:
                exc = sys.exc_info()[1]
            self.app.do_teardown_request(exc)

            # If this interpreter supports clearing the exception information
            # we do that now.  This will only go into effect on Python 2.x,
            # on 3.x it disappears automatically at the end of the exception
            # stack.
            if hasattr(sys, 'exc_clear'):
                sys.exc_clear()

        rv = _request_ctx_stack.pop()
        assert rv is self, 'Popped wrong request context.  (%r instead of %r)' \
            % (rv, self)
        if app_ctx is not None:
            app_ctx.pop(exc)

    def __enter__(self):
        from .notification import init_notification_list
        self.push()
        init_notification_list()

        return self

    def __exit__(self, exc_type, exc_value, tb):
        self.pop(exc_value)
