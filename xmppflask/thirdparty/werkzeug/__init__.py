# -*- coding: utf-8 -*-
"""
    xmppflask.thirdparty.werkzeug
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Set of objects and functions from werkzeug project that are very useful
    for XmppFlask.

    :copyright: (c) 2012 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

from .datastructures import ImmutableDict, ModificationTrackingDict, MultiDict
from .local import LocalProxy, LocalStack
from .routing import get_converter, parse_rule
from .utils import import_string
