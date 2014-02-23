# -*- coding: utf-8 -*-
"""
    xmppflask.sessions.redis
    ~~~~~~~~~~~~~~~~~~~~~~~~

    XmppFlask sessions storage in Redis.

    :copyright: (c) 2014 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

redis = __import__('redis')
import json
from . import Session, SessionInterface


class RedisSessionInterface(SessionInterface):
    """Session interface that uses Redis as session storage.

    :param host: Redis server host. Default: 'localhost'.
    :type host: str

    :param port: Redis server port. Default: 6379.
    :type host: int

    :param namespace: Key namespace. Should contains placeholder for JID value.
                      Example: ``myapp:%s``
    :type namespace: str
    """
    session_class = Session

    #: Default redis key namespace. Should contains placeholder for jid mixin.
    #: Note, that key collisions are possible if you'll launch two or more
    #  XmppFlask apps against single Redis server with same namespace value.
    namespace = 'xmppflask:sessions:%s'

    def __init__(self, host='localhost', port=6379, namespace=None):
        self.namespace = namespace or self.namespace
        self._storage = redis.Redis(host, port)

    def open_session(self, app, request):
        jid = request.environ['xmpp.jid']
        key = self.namespace % jid
        session = self.storage.get(key)
        if session is None:
            return self.session_class(_jid=jid)
        try:
            return self.session_class(**json.loads(session))
        except ValueError: # in case of invalid serialized session
            app.logger.error('Malformed session loaded: %r' % session)
            return self.session_class(_jid=jid)

    def save_session(self, app, session, response):
        key = self.namespace % session.jid
        if session.permanent:
            self.storage[key] = json.dumps(session)
        else:
            self.storage.setex(key, json.dumps(session), app.session_ttl)

    def is_session_expired(self, app, session):
        key = self.namespace % session.jid
        return self.storage.ttl(key) != -1
