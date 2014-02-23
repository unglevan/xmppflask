# -*- coding: utf-8 -*-
"""
    xmppflask.server.sleekxmpp
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    XMPPWSGI server based on SleekXMPP library.

    :copyright: (c) 2014 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

import time
import caps
from . import XmppWsgiServer
from .helpers import maybe_unicode
from .. import JID

sleekxmpp = __import__('sleekxmpp')


class SleekXmppCapability(caps.Capability):
    pass


class SleekXmppWsgiServer(XmppWsgiServer):
    """XMPPWSGI server based on SleekXMPP library."""

    capability_class = SleekXmppCapability

    def __init__(self, *args, **kwargs):
        self.module = sleekxmpp
        self.message_class = sleekxmpp.Message
        self.presence_class = sleekxmpp.Presence
        self.iq_class = sleekxmpp.Iq
        super(SleekXmppWsgiServer, self).__init__(*args, **kwargs)

    def connect(self, jid, pwd, use_tls=True, use_ssl=False):
        self.xmpp = self.module.ClientXMPP(jid, pwd)

        self.xmpp.add_event_handler('session_start', self.session_start)

        self.xmpp.connect(use_tls=use_tls, use_ssl=use_ssl)

        jid = self.xmpp.boundjid
        self.base_environ['app.jid'] = JID(jid.full)
        self.base_environ['app.protocol'] = ('tls' if use_tls else
                                             'ssl' if use_ssl else
                                             None)

    def session_start(self, session):
        super(SleekXmppWsgiServer, self).session_start()
        self.xmpp.send_presence()

    def serve_forever(self):
        self.xmpp.process(block=False)


class Standard(caps.Standard, SleekXmppCapability):

    def __init__(self, server):
        super(Standard, self).__init__(server)
        self.client.register_plugin('xep_0030')
        self.client.add_event_handler('message', self.handle_message)
        self.client.add_event_handler('presence', self.handle_presence)

    def update_environ(self, environ, stanza):
        environ['xmpp.id'] = maybe_unicode(stanza['id'])

        jid = stanza['from']
        environ['xmpp.jid'] = JID(jid.full)
        environ['xmpp.stanza_type'] = maybe_unicode(stanza['type'])

        environ['xmpp.xml'] = unicode(stanza)
        if isinstance(stanza, self.server.message_class):
            environ['xmpp.body'] = maybe_unicode(stanza['body'])
        elif isinstance(stanza, self.server.presence_class):
            environ['xmpp.priority'] = stanza['priority']
            environ['xmpp.body'] = maybe_unicode(stanza['status'])
            environ['xmpp.status'] = maybe_unicode(stanza['show'])

    def cmd_message(self, environ, payload):
        """Sends XMPP messages.

        :param environ: XMPPWSGI environ.
        :type environ: dict

        :param payload: Message payload data.
        :type payload: dict

        :returns: True
        """
        to_jid = JID(payload.get('to', environ['xmpp.jid']))

        if environ['xmpp.stanza_type'] == 'groupchat':
            to_jid = to_jid.bare
        else:
            to_jid = to_jid.full

        self.client.send_message(
            mto=to_jid,
            mbody=payload['body'],
            mtype=environ['xmpp.stanza_type'])
        return True

    def cmd_presence(self, environ, payload):
        """Sends XMPP presence event.

        :param environ: XMPPWSGI environ.
        :type environ: dict

        :param payload: Presence payload data.
        :type payload: dict

        :returns: True
        """
        to_jid = payload.get('to', environ['xmpp.jid'])

        if to_jid == 'all':
            to_jid = None
        elif isinstance(to_jid, JID):
            to_jid = to_jid.full

        if 'type' not in payload:
            self.client.send_presence(pto=to_jid)
        elif payload['type'] in ('available', 'unavailable'):
            self.client.send_presence(pto=to_jid, ptype=payload['type'])
        elif payload['type'] in ('subscribe', 'subscribed',
                                 'unsubscribe', 'unsubscribed', 'probe'):
            self.client.send_presence(pto=to_jid, ptype=payload['type'])
        else:
            self.client.send_presence(pto=to_jid,
                                      pstatus=payload.get('status', ''),
                                      pshow=payload['type'])
        return True

    def cmd_iq(self, environ, payload):
        raise NotImplementedError


class Delay(caps.Delay, SleekXmppCapability):

    def __init__(self, *args, **kwargs):
        super(Delay, self).__init__(*args, **kwargs)
        self.client.register_plugin('xep_0203')

    def update_environ(self, environ, stanza):
        if 'delay' not in stanza.plugins:
            return

        delay = time.mktime(
            stanza.plugins['delay'].get_stamp().utctimetuple()
        )
        environ['xmpp.delay'] = environ['xmpp.timestamp'] - delay


class Version(caps.Version, SleekXmppCapability):

    def __init__(self, *args, **kwargs):
        super(Version, self).__init__(*args, **kwargs)
        self.client.register_plugin('xep_0092')
        self.client.plugin['xep_0092'].software_name = '/'.join([
            self.software, 'SleekXMPP'])
        self.client.plugin['xep_0092'].version = self.version
        self.client.plugin['xep_0092'].os = self.os

    def cmd_version(self, environ, payload):
        """Returns software version of remote user.

        :param environ: XMPPWSGI environ.
        :type environ: dict

        :param payload: Payload data.
        :type payload: dict

        :returns: Software version info dict with keys: `os`, `name`, `version`
        :rtype: dict
        """
        jid = payload.get('jid', environ['xmpp.jid'])
        if isinstance(jid, JID):
            jid = jid.full

        try:
            resp = self.client.plugin['xep_0092'].get_version(jid)
            if resp:
                return resp
        except Exception:
            self.app.logger.exception('Failed to retrieve version info for %s',
                                      jid)
            return None


class Muc(caps.Muc, SleekXmppCapability):

    def __init__(self, *args, **kwargs):
        super(Muc, self).__init__(*args, **kwargs)
        self.client.register_plugin('xep_0045')

    def cmd_join_room(self, environ, payload):
        """Joins to the specified MUC room.

        :param environ: XMPPWSGI environ.
        :type environ: dict

        :param payload: Payload data.
        :type payload: dict
        """
        self.client.plugin['xep_0045'].joinMUC(
            room=payload['room'],
            nick=payload['nick'],
            password=payload.get('password')
        )
