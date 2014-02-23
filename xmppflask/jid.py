# -*- coding: utf-8 -*-
"""
    xmppflask.jid
    ~~~~~~~~~~~~~

    This module allows for working with Jabber IDs (JIDs) by
    providing accessors for the various components of a JID.

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2011 Nathanael C. Fritz
    :license: MIT, see LICENSE for more details
"""

from __future__ import unicode_literals


class JID(object):

    """
    A representation of a Jabber ID, or JID.

    Each JID may have three components: a user, a domain, and an optional
    resource. For example: user@domain/resource

    When a resource is not used, the JID is called a bare JID.
    The JID is a full JID otherwise.

    **JID Properties:**

        :full: The value of the full JID.
        :bare: The value of the bare JID.
        :node: The node name portion of the JID.
        :domain: The domain name portion of the JID.
        :resource: The resource portion of the JID.
        :jid: Alias for ``full``.
        :user: Alias for ``node``.
        :host: Alias for ``domain``.
        :server: Alias for ``domain``.

    :param string jid: A string of the form ``'[user@]domain[/resource]'``.
    """

    __slots__ = ('_jid', '_bare', '_node', '_domain', '_resource')

    def __init__(self, jid):
        """Initialize a new JID"""
        self.reset(jid)

    def reset(self, jid):
        if isinstance(jid, JID):
            jid = jid.full
        self._jid = jid
        self._domain = None
        self._resource = None
        self._node = None
        self._bare = None

    def regenerate(self):
        """Generate a new JID based on current values, useful after editing."""
        jid = ""
        if self.user:
            jid = "%s@" % self.user
        jid += self.domain
        if self.resource:
            jid += "/%s" % self.resource
        self.reset(jid)

    def __str__(self):
        """Use the full JID as the string value."""
        return self.full

    def __repr__(self):
        return '<xmppflask.JID %s>' % self.jid

    def __eq__(self, other):
        """
        Two JIDs are considered equal if they have the same full JID value.
        """
        other = JID(other)
        return self.full == other.full

    def __ne__(self, other):
        """Two JIDs are considered unequal if they are not equal."""
        return not self == other

    def __hash__(self):
        """Hash a JID based on the string version of its full JID."""
        return hash(self.full)

    def __copy__(self):
        """Returns copy instance of this JID"""
        return JID(self.full)

    @property
    def node(self):
        if self._node is None:
            if '@' in self._jid:
                self._node = self._jid.split('@', 1)[0]
        return self._node or ""

    @node.setter
    def node(self, value):
        assert isinstance(value, basestring)
        self._node = value
        self.regenerate()

    @property
    def domain(self):
        if self._domain is None:
            self._domain = self._jid.split('@', 1)[-1].split('/', 1)[0]
        return self._domain or ""

    @domain.setter
    def domain(self, value):
        assert value and isinstance(value, basestring)
        self._domain = value

    @property
    def resource(self):
        if self._resource is None and '/' in self._jid:
            self._bare, self._resource = self._jid.split('/', 1)
        return self._resource or ""

    @resource.setter
    def resource(self, value):
        assert isinstance(value, basestring)
        self._resource = value
        self.regenerate()

    @property
    def bare(self):
        if self._bare is None:
            self._bare = self._jid.split('/', 1)[0]
        return self._bare or ""

    @bare.setter
    def bare(self, value):
        assert value and isinstance(value, basestring)
        if '@' in value:
            self._node, self._domain = value.split('@', 1)
        else:
            self._node, self._domain = '', value
        self.regenerate()

    @property
    def full(self):
        return self._jid

    @full.setter
    def full(self, value):
        self.reset(value)
        self.regenerate()

    # Aliases
    jid = full
    user = node
    host = server = domain
