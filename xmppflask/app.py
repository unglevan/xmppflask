# -*- coding: utf-8 -*-
"""
    xmppflask.app
    ~~~~~~~~~~~~~

    This module implements the central XMPPWSGI-like application object.

    :copyright: (c) 2014 Kostyantyn Rybnikov <k.bx@ya.ru>
    :license: BSD
"""

import sys
from threading import Lock
from itertools import chain

from .config import ConfigAttribute, Config
from .ctx import RequestContext, AppContext, _AppCtxGlobals
from .exceptions import NotFound
from .globals import _request_ctx_stack
from .helpers import (
    _endpoint_from_view_func, locked_cached_property, _PackageBoundObject
)
from .logger import create_logger
from .routing import Map, Rule
from .templating import (
    DispatchingJinjaLoader, Environment, _default_template_ctx_processor
)
from .sessions import SessionInterface
from .wrappers import Request, Response
from .thirdparty.werkzeug import ImmutableDict

# a lock used for logger initialization
_logger_lock = Lock()


class XmppFlask(_PackageBoundObject):
    debug = ConfigAttribute('DEBUG')
    session_ttl = ConfigAttribute('SESSION_TTL')

    debug_log_format = (
        '-' * 80 + '\n' +
        '%(levelname)s in %(module)s [%(pathname)s:%(lineno)d]:\n' +
        '%(message)s\n' +
        '-' * 80
    )

    #: Default configuration parameters.
    default_config = ImmutableDict({
        'DEBUG': True,
        #: Non permanent session lifetime in seconds. One hour by default.
        'SESSION_TTL': 3600
    })

    #: The rule object to use for route rules created.  This is used by
    #: :meth:`add_route_rule`. Defaults to :class:`xmppflask.routing.Rule`.
    route_rule_class = Rule

    app_ctx_globals_class = _AppCtxGlobals
    request_class = Request
    response_class = Response
    session_interface = SessionInterface()

    #: Options that are passed directly to the Jinja2 environment.
    jinja_options = ImmutableDict(
        extensions=['jinja2.ext.with_']
    )

    def __init__(self, import_name, template_folder='templates'):
        from .helpers import get_package_path

        super(XmppFlask, self).__init__(import_name,
                                        template_folder=template_folder)

        self.import_name = import_name
        self.root_path = get_package_path(self.import_name)

        self.config = Config(self.root_path, self.default_config)

        #: Prepare the deferred setup of the logger.
        self._logger = None
        self.logger_name = self.import_name

        #: To register a view function, use the :meth:`route` decorator.
        self.view_functions = {}

        #: A dictionary with lists of functions that should be called at the
        #: beginning of the request.
        self.before_request_funcs = {}

        #: A dictionary with lists of functions that should be called after
        #: each request.
        self.after_request_funcs = {}

        #: A dictionary with lists of functions that are called after
        #: each request, even if an exception has occurred.
        self.teardown_request_funcs = {}

        #: A list of functions that are called when the application context
        #: is destroyed.
        self.teardown_appcontext_funcs = []

        #: A dictionary with functions that are mapped to exception class to
        #: be called when binded error occurred due request processing.
        self.exception_handle_funcs = {}

        self.route_map = Map()

        #: A dictionary with list of functions that are called without argument
        #: to populate the template context.
        self.template_context_processors = {
            None: [_default_template_ctx_processor]
        }

        #: all the attached blueprints in a directory by name.
        self.blueprints = {}

        #: A dictionary with lists of functions that can be used as route value
        #: preprocessors.
        self.route_default_functions = {}

        #: A list of XMPPWSGI server capabilities names (XEPs) which
        #: XMPPWSGI server MUST implement.
        self.required_capabilities = set()

    def route(self, rule, **options):
        """A decorator that is basically a regexp to provide a link between
        message and it's handler func. Example::

            @app.route('PING')
            def index():
                return 'PONG'

        :param rule: the message rule as unicode string
        """

        def decorator(f):
            self.add_route_rule(rule, None, f, event_type='message', **options)
            return f

        return decorator

    route_message = route

    def route_presence(self, **options):
        """A decorator that's provides a link between presence event and
        his handler func. Example::

            @app.route_presence(from_jid='*@xmpp.ru)
            def index():
                if 'handled_presences' not in session:
                    session['handled_presences'] = 0
                session['handled_presences'] += 1
        """

        def decorator(f):
            self.add_route_rule(None, None, f, event_type='presence', **options)
            return f

        return decorator

    def add_route_rule(self, rule, endpoint=None, view_func=None, **options):
        """Connect route rule. Works exactly like the :meth:`route` decorator.
        Except for endpoint param.

        :param rule:     the message rule as unicode string
        :param endpoint: the endpoint for the registered route rule.  XmppFlask
                         itself assumes the name of the view function as
                         endpoint
        """
        if endpoint is None:
            endpoint = _endpoint_from_view_func(view_func)
        options['endpoint'] = endpoint
        rule = self.route_rule_class(rule, **options)
        self.route_map.add(rule)
        if view_func is not None:
            self.view_functions[endpoint] = view_func

    @property
    def logger(self):
        """A :class:`logging.Logger` object for this application.  The
        default configuration is to log to stderr if the application is
        in debug mode.  This logger can be used to (surprise) log messages.
        Here some examples::

            app.logger.debug('A value for debugging')
            app.logger.warning('A warning occurred (%d apples)', 42)
            app.logger.error('An error occurred')
        """
        if self._logger and self._logger.name == self.logger_name:
            return self._logger
        with _logger_lock:
            if self._logger and self._logger.name == self.logger_name:
                return self._logger
            self._logger = rv = create_logger(self)
            return rv

    def __call__(self, environ, notification_queue=None):
        """Shortcut for :attr:`xmppwsgi_app`."""
        return self.xmppwsgi_app(environ, notification_queue)

    def xmppwsgi_app(self, environ, notification_queue=None):
        """The actual XMPPWSGI application

        It's a bit simpler then actual wsgi :-) I don't think it needs
        ``start_response`` or something. More should be discussed
        somewhere later.
        """
        from .notification import get_notification_list

        with self.request_context(environ):
            # TODO: maybe something like this would be better
            # try:
            #     response = self.full_dispatch_request()
            # except Exception, e:
            #     response = self.make_response(self.handle_exception(e))
            response = self.full_dispatch_request()
            for item in get_notification_list():
                notification_queue.append(item)
            return response

    def run(self, jid, pwd, engine=None):
        """Starts server for this XMPPWSGI application.

        :param jid: Application JID.
        :type jid: str

        :param pwd: Password for specified JID.
        :type pwd: str

        :param engine: XMPP backend library. Currently supported xmpppy and
                       SleekXMPP. Possible shortcuts: xmpp, sleek. Values are
                       case insensitive.
        :type engine: str

        :raises:
            :exc:`ValueError`: If specified engine is not supported.
            :exc:`ImportError`: If specified engine is supported, but his
                                package is missed.
        """
        import xmppflask.run as do # just for nicer code

        return do.run_server(self, jid, pwd, engine)

    def open_session(self, request):
        """Creates or opens a new session. Instead of overriding this method
        we recommend replacing the :class:`session_interface`.

        :param request: an instance of :attr:`request_class`.
        """
        return self.session_interface.open_session(self, request)

    def save_session(self, session, response):
        """Saves the session if it needs updates. For the default
        implementation, check :meth:`open_session`. Instead of overriding this
        method we recommend replacing the :class:`session_interface`.

        :param session: the session to be saved
        :param response: an instance of :attr:`response_class`
        """
        return self.session_interface.save_session(self, session, response)

    def make_null_session(self):
        """Creates a new instance of a missing session.  Instead of overriding
        this method we recommend replacing the :class:`session_interface`.
        """
        return self.session_interface.make_null_session(self)

    def do_teardown_request(self, exc=None):
        """Called after the actual request dispatching and will
        call every as :meth:`teardown_request` decorated function.  This is
        not actually called by the :class:`XmppFlask` object itself but is
        always triggered when the request context is popped.  That way we have
        a tighter control over certain resources under testing environments.
        """
        if exc is None:
            exc = sys.exc_info()[1]
        funcs = reversed(self.teardown_request_funcs.get(None, ()))
        for func in funcs:
            rv = func(exc)
            if rv is not None:
                return rv

    def do_teardown_appcontext(self, exc=None):
        """Called when an application context is popped.  This works pretty
        much the same as :meth:`do_teardown_request` but for the application
        context.
        """
        if exc is None:
            exc = sys.exc_info()[1]
        for func in reversed(self.teardown_appcontext_funcs):
            func(exc)

    def app_context(self):
        """Binds the application only.  For as long as the application is bound
        to the current context the :data:`xmppflask.current_app` points to that
        application.  An application context is automatically created when a
        request context is pushed if necessary.
        """
        return AppContext(self)

    def request_context(self, environ):
        """Creates a :class:`~xmppflask.ctx.RequestContext` from given
        environment and binds it to the current context."""

        return RequestContext(self, environ)

    def preprocess_request(self):
        """Called before the actual request dispatching and will
        call every as :meth:`before_request` decorated function.
        If any of these function returns a value it's handled as
        if it was the return value from the view and further
        request handling is stopped.
        """
        funcs = self.before_request_funcs.get(None, ())
        for func in funcs:
            rv = func()
            if rv is not None:
                return rv

    def process_response(self, response):
        """Can be overridden in order to modify the response object
        before it's sent to the XMPPWSGI server. By default this will
        call all the :meth:`after_request` decorated functions.

        :param response: a :attr:`response_class` object.
        :return: a new response object or the same, has to be an
                 instance of :attr:`response_class`.
        """
        ctx = _request_ctx_stack.top
        bp = ctx.request.blueprint # TODO: does this really needed?
        if not self.session_interface.is_null_session(ctx.session):
            self.save_session(ctx.session, response)
        funcs = ()
        if bp is not None and bp in self.after_request_funcs:
            funcs = reversed(self.after_request_funcs[bp])
        if None in self.after_request_funcs:
            funcs = chain(funcs, reversed(self.after_request_funcs[None]))
        for handler in funcs:
            response = handler(response)
        return response

    def full_dispatch_request(self):
        try:
            rv = self.preprocess_request()
            if rv is None:
                rv = self.dispatch_request()
        except Exception, e:
            rv = self.handle_user_exception(e)
        response = self.make_response(rv)
        response = self.process_response(response)
        return response

    def dispatch_request(self):
        req = _request_ctx_stack.top.request
        if req.routing_exception is not None:
            raise req.routing_exception
        rule = req.route_rule
        return self.view_functions[rule.endpoint](**req.view_args)

    def create_route_adapter(self, request):
        """Creates a route adapter for the given request.  The route adapter
        is created at a point where the request context is not yet set up
        so the request is passed explicitly.
        """
        return self.route_map.bind_to_environ(request.environ)

    def make_response(self, rv):
        """Converts the return value from a view function to a real
        response object that is an instance of :attr:`response_class`."""
        if isinstance(rv, self.response_class):
            return rv
        return self.response_class(rv)

    def update_template_context(self, context):
        """Update the template context with some commonly used variables.
        This injects request, session, config and g into the template
        context as well as everything template context processors want
        to inject.

        :param context: the context as a dictionary that is updated in place
                        to add extra variables.
        """
        funcs = self.template_context_processors[None]
        orig_ctx = context.copy()
        for func in funcs:
            context.update(func())
            # make sure the original values win.  This makes it possible to
        # easier add new variables in context processors without breaking
        # existing views.
        context.update(orig_ctx)

    @locked_cached_property
    def jinja_env(self):
        """The Jinja2 environment used to load templates."""
        rv = self.create_jinja_environment()
        return rv

    def create_jinja_environment(self):
        """Creates the Jinja2 environment based on :attr:`jinja_options`
        and :meth:`select_jinja_autoescape`.  This also adds
        the Jinja2 globals and filters after initialization.  Override
        this function to customize the behavior.
        """
        from .helpers import message_for

        options = dict(self.jinja_options)
        rv = Environment(self, **options)
        rv.globals.update(
            message_for=message_for,
        )
        return rv

    def create_global_jinja_loader(self):
        """Creates the loader for the Jinja2 environment.  Can be used to
        override just the loader and keeping the rest unchanged.  It's
        discouraged to override this function.  Instead one should override
        the :meth:`create_jinja_loader` function instead.

        The global loader dispatches between the loaders of the application
        and the individual blueprints.
        """
        return DispatchingJinjaLoader(self)

    def inject_route_defaults(self, endpoint, values):
        """Injects the route defaults for the given endpoint directly into
        the values dictionary passed.  This is used internally and
        automatically called on URL building.
        """
        funcs = self.route_default_functions.get(None, ())
        if '.' in endpoint:
            bp = endpoint.split('.', 1)[0]
            funcs = chain(funcs, self.route_default_functions.get(bp, ()))
        for func in funcs:
            func(endpoint, values)

    def handle_user_exception(self, e):
        """This method is called whenever an exception occurs that should be
        handled.
        """
        handler = None
        funcs = self.exception_handle_funcs
        if e in funcs:  # maybe we have direct match
            handler = funcs[e]

        for err, func in funcs.items():  # or just handler by base exc class
            if isinstance(e, err):
                handler = func
                break

        if isinstance(e, NotFound) and handler is not None:
            return handler(e)
        elif isinstance(e, NotFound):
            return

        self.logger.exception(e)

        if handler is None:
            if self.debug:
                raise e
        else:
            return handler(e)

        return u'Some application error happened. Probably that\'s my bug :)'

    def before_request(self, f):
        """Registers a function to run before each request."""
        self.before_request_funcs.setdefault(None, []).append(f)
        return f

    def teardown_request(self, f):
        """Register a function to be run at the end of each request,
        regardless of whether there was an exception or not.  These functions
        are executed when the request context is popped, even if not an
        actual request was performed.
        """
        self.teardown_request_funcs.setdefault(None, []).append(f)
        return f

    def teardown_appcontext(self, f):
        """Registers a function to be called when the application context
        ends.  These functions are typically also called when the request
        context is popped.
        """
        self.teardown_appcontext_funcs.append(f)
        return f

    def on_error(self, exception_class):
        """Register a function to be run when `exception_class` occurred due
         request processing."""

        def wrapper(f):
            self.exception_handle_funcs[exception_class] = f
            return f

        return wrapper

    def require_capability(self, name):
        """Register XMPPWSGI server capability name as required one."""
        self.required_capabilities.add(name)
