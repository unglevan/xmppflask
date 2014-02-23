# -*- coding: utf-8 -*-
"""
    xmppflask.notification
    ~~~~~~~~~~~~~~~~~~~~~~

    Notification collecting logic.

    :copyright: (c) 2014 Kostyantyn Rybnikov <k.bx@ya.ru>
    :license: BSD
"""

from . import g

def notify(jid, message):
    g._notification_list.append((jid, message))

def init_notification_list():
    g._notification_list = []

def get_notification_list():
    if g._notification_list:
        return g._notification_list
    return []
