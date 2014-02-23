# -*- coding: utf-8 -*-
"""
    xmppflask.server.xmpppy
    ~~~~~~~~~~~~~~~~~~~~~~~

    XMPPWSGI server based on xmpppy library.

    :copyright: (c) 2014 Alexander Shorin <kxepal@gmail.com>
    :license: BSD
"""

import datetime
import time
import caps
from . import XmppWsgiServer
from .helpers import maybe_unicode, gen_id
from .. import JID

import xmpp


class XmpppyCapability(caps.Capability):
    pass


class XmpppyWsgiServer(XmppWsgiServer):
    """XMPPWSGI server based on xmpppy library."""

    capability_class = XmpppyCapability

    def __init__(self, *args, **kwargs):
        self.module = xmpp
        self.message_class = xmpp.Message
        self.presence_class = xmpp.Presence
        self.iq_class = xmpp.Iq
        super(XmpppyWsgiServer, self).__init__(*args, **kwargs)

    def connect(self, jid, pwd, use_tls=True, use_ssl=False):
        jid = JID(jid)
        user, server, password = jid.user, jid.domain, pwd

        self.xmpp = self.module.Client(server)

        conn_type = self.xmpp.connect()

        if conn_type is None:
            raise Exception(u'Unable to connect to server %s!' % server)

        auth_type = self.xmpp.auth(user, password)

        if auth_type is None:
            raise Exception((u'Unable to authorize on %s - '
                             u'check login/password.') % server)
        self.session_start()

        self.base_environ['app.jid'] = jid
        self.base_environ['app.protocol'] = self.xmpp.connected

    def session_start(self):
        super(XmpppyWsgiServer, self).session_start()
        self.xmpp.sendInitPresence()

    def serve_forever(self):
        def step_on(conn):
            try:
                conn.Process(1)
            except KeyboardInterrupt:
                return False
            return True

        while step_on(self.xmpp):
            pass


class Standard(caps.Standard, XmpppyCapability):

    def __init__(self, server):
        super(Standard, self).__init__(server)
        self.client.RegisterHandler('message',
                                    lambda c, s: self.handle_message(s))
        self.client.RegisterHandler('presence',
                                    lambda c, s: self.handle_presence(s))

    def update_environ(self, environ, stanza):
        environ['xmpp.id'] = maybe_unicode(maybe_unicode(stanza.getID()))

        environ['xmpp.jid'] = JID(str(stanza.getFrom()))
        environ['xmpp.stanza_type'] = maybe_unicode(stanza.getType())

        environ['xmpp.xml'] = unicode(stanza)
        if isinstance(stanza, self.server.message_class):
            environ['xmpp.body'] = maybe_unicode(stanza.getBody())
        elif isinstance(stanza, self.server.presence_class):
            environ['xmpp.priority'] = stanza.getPriority()
            environ['xmpp.body'] = maybe_unicode(stanza.getStatus())
            environ['xmpp.status'] = maybe_unicode(stanza.getShow())

        return environ

    def cmd_message(self, environ, payload):
        """Sends XMPP message.

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

        msg = self.server.message_class(to_jid, payload['body'])
        msg.setType(environ['xmpp.stanza_type'])
        msg.setID(gen_id())
        self.client.send(msg)
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

        presence_cls = self.server.presence_class
        if 'type' not in payload:
            presence = presence_cls(to=to_jid)
        elif payload['type'] in ('available', 'unavailable'):
            presence = presence_cls(to=to_jid, typ=payload['type'])
        elif payload['type'] in ('subscribe', 'subscribed',
                                 'unsubscribe', 'unsubscribed'):
            presence = presence_cls(to=to_jid, typ=payload['type'])
        elif payload['type'] in ('probe',):
            presence = presence_cls(to=to_jid, typ=payload['type'])
        else:
            presence = presence_cls(to=to_jid, status=payload.get('status', ''),
                                    show=payload['type'])
        self.client.send(presence)
        return True

    def cmd_iq(self, environ, payload):
        raise NotImplementedError


class Delay(caps.Delay, XmpppyCapability):

    def update_environ(self, environ, stanza):
        delay = stanza.getTimestamp()
        if delay:
            delay = time.mktime(
                datetime.datetime.strptime(delay,
                                           '%Y%m%dT%H:%M:%S').utctimetuple()
            )
            environ['xmpp.delay'] = environ['xmpp.timestamp'] - delay


class Version(caps.Version, XmpppyCapability):

    def __init__(self, *args, **kwargs):
        super(Version, self).__init__(*args, **kwargs)

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

        iq = self.server.iq_class('get')
        iq.setID(gen_id())
        iq.addChild('query', {}, [], 'jabber:iq:version')
        iq.setTo(jid)
        res = self.client.SendAndWaitForResponse(iq, timeout=5)

        if res is None:
            return
        if res.getType() != 'result':
            return

        info = {
            'os': None,
            'name': None,
            'version': None
        }

        for prop in res.getQueryChildren():
            name = prop.getName()
            if name in info:
                info[name] = prop.getData()

        return info


class Muc(caps.Muc, XmpppyCapability):

    def cmd_join_room(self, environ, payload):
        """Joins to the specified MUC room.

        :param environ: XMPPWSGI environ.
        :type environ: dict

        :param payload: Payload data.
        :type payload: dict
        """
        jid = JID(payload['room'])
        jid.resource = payload['nick']
        presence = self.server.presence_class(to=jid.full)
        body = presence.setTag('x', namespace=xmpp.NS_MUC)
        body.addChild('history', {'maxchars': '0'})
        if payload.get('password'):
            body.setTagData('password', payload['password'])
        self.client.send(presence)
