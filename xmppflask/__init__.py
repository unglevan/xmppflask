# -*- coding: utf-8 -*-
"""
    xmppflask
    ~~~~~~~~~

    A microframework, inspired by Flask.

    :copyright: (c) 2014 Kostyantyn Rybnikov <k.bx@ya.ru>
    :license: BSD
"""

__version__ = '0.0.1'

from .app import XmppFlask
from .globals import (
    current_app, environ, request, session, g,
    _app_ctx_stack, _request_ctx_stack
)
from .jid import JID
from .templating import render_template, render_template_string
from .helpers import safe_join
from .notification import notify
