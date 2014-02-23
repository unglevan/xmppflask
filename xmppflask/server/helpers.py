# -*- coding: utf-8 -*-
"""
    xmppflask.server.helpers
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Various common helpers for XMPPWSGI server needs.

    :copyright: (c) 2014 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

import uuid


def maybe_unicode(value):
    if value is None:
        return value
    if not value:
        return None
    return unicode(value)


def split_jid(jid):
    user, tail = jid.split('@', 1) if '@' in jid else ('', jid)
    domain, resource = tail.split('/', 1) if '/' in tail else (tail, '')
    return user, domain, resource


def gen_id(prefix='xmppflask'):
    return '{0}-{1}'.format(prefix, str(uuid.uuid4()).split('-')[0])
