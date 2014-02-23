# -*- coding: utf-8 -*-
"""
    xmppflask.sessions
    ~~~~~~~~~~~~~~~~~~

    XmppFlask sessions.

    :copyright: (c) 2014 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

from .base import SessionInterface, Session, NullSession
from .memory import MemorySession, MemorySessionInterface
from .redis import RedisSessionInterface
