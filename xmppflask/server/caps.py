# -*- coding: utf-8 -*-
"""
    xmppflask.server.caps
    ~~~~~~~~~~~~~~~~~~~~~

    XMPPWSGI server capabilities.

    :copyright: (c) 2014 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

import platform
import weakref
from abc import ABCMeta, abstractmethod


class CapabilityNotFound(Exception):
    """Raises when capability couldn't be or isn't loaded."""


class Capability(object):
    """Base class for XMPPWSGI server capability."""

    __metaclass__ = ABCMeta

    name = None

    def __init__(self, server):
        self.app = weakref.proxy(server.app)
        self.client = weakref.proxy(server.xmpp)
        self.server = weakref.proxy(server)

    def update_environ(self, environ, stanza):
        pass


class Standard(Capability):
    """Standard XMPPWSGI server capability."""

    name = 'std'

    def handle_message(self, stanza):
        """Handles XMPP message stanza."""
        return self.server.handle(stanza)

    def handle_presence(self, stanza):
        """Handles XMPP presence stanza."""
        return self.server.handle(stanza)

    def handle_iq(self, stanza):
        """Handles XMPP iq stanza."""
        return self.server.handle(stanza)

    @abstractmethod
    def cmd_message(self, environ, payload):
        """Should send XMPP message stanza.

        :param environ: XMPPWSGI environ.
        :type environ: dict

        :param payload: Message payload data.
        :type payload: dict

        :returns: True
        """
        raise NotImplementedError

    @abstractmethod
    def cmd_presence(self, environ, payload):
        """Should send XMPP presence stanza.

        :param environ: XMPPWSGI environ.
        :type environ: dict

        :param payload: Presence payload data.
        :type payload: dict

        :returns: True
        """
        raise NotImplementedError

    @abstractmethod
    def cmd_iq(self, environ, payload):
        """Should send XMPP IQ stanza.

        :param environ: XMPPWSGI environ.
        :type environ: dict

        :param payload: IQ payload data.
        :type payload: dict

        :returns: True
        """
        raise NotImplementedError


class Delay(Capability):
    """Capability for XEP-0203"""

    name = 'XEP-0203'


class Version(Capability):
    """Capability for XEP-0092"""

    name = 'XEP-0092'

    def __init__(self, *args, **kwargs):
        super(Version, self).__init__(*args, **kwargs)
        import xmppflask  # prevent cyclic imports
        self.software = 'XmppFlask'
        self.version = xmppflask.__version__
        self.os = self.get_os_name()

    def get_os_name(self):
        """Returns OS name for XmppFlask host.

        Example: u'Linux 3.11.6-gentoo x86_64'

        """
        return u"{0} {1} {2}".format(
            platform.system(),
            platform.release(),
            platform.machine()
        )

    @abstractmethod
    def cmd_version(self, environ, payload):
        """Returns software version of remote user.

        :param environ: XMPPWSGI environ.
        :type environ: dict

        :param payload: Payload data.
        :type payload: dict

        :returns: Software version info dict with keys: `os`, `name`, `version`
        :rtype: dict
        """
        raise NotImplementedError


class Muc(Capability):
    """Capability for XEP-0045"""

    name = 'XEP-0045'

    @abstractmethod
    def cmd_join_room(self, environ, payload):
        """Joins to the specified MUC room.

        :param environ: XMPPWSGI environ.
        :type environ: dict

        :param payload: Payload data.
        :type payload: dict
        """
        raise NotImplementedError
