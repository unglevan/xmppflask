# -*- coding: utf-8 -*-
"""
    xmppflask.server
    ~~~~~~~~~~~~~~~~

    XMPPWSGI server implementations to serve XmppFlask apps.

    :copyright: (c) 2014 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

from .base import XmppWsgiServer
from .caps import Capability, CapabilityNotFound
