# -*- coding: utf-8 -*-
"""
    xmppflask.sessions.base
    ~~~~~~~~~~~~~~~~~~~~~~~

    Common sessions workflow.

    :copyright: (c) 2014 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

from ..thirdparty.werkzeug import ModificationTrackingDict


class SessionMixin(object):
    """Expands a basic dictionary with an accessors that are expected
    by Flask extensions and users for the session.
    """

    def _get_permanent(self):
        return self.get('_permanent', False)

    def _set_permanent(self, value):
        self['_permanent'] = bool(value)

    #: this reflects the ``'_permanent'`` key in the dict.
    permanent = property(_get_permanent, _set_permanent)
    del _get_permanent, _set_permanent

    #: some session backends can tell you if a session is new, but that is
    #: not necessarily guaranteed.  Use with caution.  The default mixin
    #: implementation just hardcodes `False` in.
    new = False

    #: for some backends this will always be `True`, but some backends will
    #: default this to false and detect changes in the dictionary for as
    #: long as changes do not happen on mutable structures in the session.
    #: The default mixin implementation just hardcodes `True` in.
    modified = True


class Session(ModificationTrackingDict, SessionMixin):
    """Base dict-like XmppFlask session class."""

    def _get_jid(self):
        return self.get('_jid')

    def _set_jid(self, value):
        self['_jid'] = value

    #: reflects the ``'_jid'`` key that points whom this session belongs to.
    jid = property(_get_jid, _set_jid)


class NullSession(Session):
    """Dummy NullSession that does nothing."""

    def __setitem__(self, *args, **kwargs):
        pass
    __delitem__ = clear = pop = popitem = update = setdefault = __setitem__

    def _set_jid(self, value):
        # we shouldn't care about whom belongs nulled session.
        pass


class SessionInterface(object):
    """The basic interface you have to implement in order to replace the
    default session interface."""

    null_session_class = NullSession

    _storage = None

    def make_null_session(self, app):
        """Creates a null session which acts as a replacement object if the
        real session support could not be loaded due to a configuration
        error.  This mainly aids the user experience because the job of the
        null session is to still support lookup without complaining but
        modifications are answered with a helpful error message of what
        failed.

        This creates an instance of :attr:`null_session_class` by default.
        """
        return self.null_session_class()

    def is_null_session(self, obj):
        """Checks if a given object is a null session. Null sessions are
        not asked to be saved.

        This checks if the object is an instance of :attr:`null_session_class`
        by default.
        """
        return isinstance(obj, self.null_session_class)

    def is_session_expired(self, app, session):
        """Helper to locate expired sessions.. Should return :class:`bool`.
        By default counts all session actual."""
        return False

    def open_session(self, app, request):
        """This method has to be implemented and must either return `None`
        in case the loading failed because of a configuration error or an
        instance of a session object which implements a dictionary like
        interface + the methods and attributes on :class:`SessionMixin`.
        """
        return None

    def save_session(self, app, session, response):
        """This is called for actual sessions returned by :meth:`open_session`
        at the end of the request.  This is still called during a request
        context so if you absolutely need access to the request you can do
        that.
        """
        return None

    @property
    def storage(self):
        """Session storage proxy."""
        return self._storage
