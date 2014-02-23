# -*- coding: utf-8 -*-
"""
    xmppflask.sessions.memory
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    In-memory sessions implementation.

    :copyright: (c) 2014 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

import time
from threading import Lock
from . import Session, SessionInterface


class MemorySession(Session):
    """Expands the session with support for switching between permanent
    and non-permanent sessions."""

    _timestamp = None

    @property
    def should_save(self):
        """True if the session should be saved."""
        return self.modified

    @property
    def timestamp(self):
        """Last session update timestamp."""
        return self._timestamp

    def on_update(self):
        """Updates session timestamp value."""
        self._timestamp = time.time()
        return super(Session, self).on_update()


class MemorySessionInterface(SessionInterface):
    """The session interface that keeps all sessions in memory."""

    session_class = MemorySession

    def __init__(self, *args, **kwargs):
        self._storage = {}
        self._lock = Lock()
        super(MemorySessionInterface, self).__init__(*args, **kwargs)

    def open_session(self, app, request):
        self.cleanup(app)
        jid = request.environ['xmpp.jid']
        session = self.storage.get(jid)
        if session is None:
            session = self.session_class()
            session.jid = jid
        return session

    def save_session(self, app, session, response):
        self.storage[session.jid] = session
        self.cleanup(app)

    def is_session_expired(self, app, session):
        if session.permanent:
            return False
        if session.timestamp is None:
            return False
        return session.timestamp + app.session_ttl < time.time()

    def cleanup(self, app):
        with self._lock:
            for key, session in self.storage.items():
                if self.is_session_expired(app, session):
                    del self.storage[key]
