# -*- coding: utf-8 -*-
"""
    xmpp_wsgi_runner for xmppflask (or just XMPPWSGI)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This application is intended to be something like a web server bug for
    XMPPWSGI and serve XMPPWSGI applications. It is kept simple, but
    potentially can be rewritten to handle more load. Future plans are also
    support of gevent-like coroutines, but we will need to try to import
    gevent's monkey.patch_sockets() to PyPy somehow.

    :copyright: (c) 2014 Kostyantyn Rybnikov <k.bx@ya.ru>
    :license: BSD
"""

import getopt
import getpass
import os
import sys

_HELP = '''
usage: %(name)s [-h] [--jid=JID] [--password=PASSWORD] [--engine=ENGINE] app

Runs XMPPWSGI server to serve XmppFlask apps.

positional arguments:
  app                  a path to application python file and variable in it
                       separated by ":". For example:
                       ./cool_weather/weather.py:app means that application is
                       in file ./cool_weather/weather.py and stored in
                       variable called app

optional arguments:
  -h, --help           show this help message and exit
  --jid=JID            JID of a bot. You might want to register one for your
                       bot. Also it could be setted via XMPPFLASK_JID variable
                       or be omitted to be asked to promt.
  --password=PASSWORD  password to that jid. Also, it could be setted via
                       XMPPFLASK_PASSWORD variable. Finally, if password is
                       not given it will be asked from tty.
  --engine=ENGINE      XMPP backend library. Currently supported xmpppy and
                       SleekXMPP. Possible shortcuts: xmpp, sleek. Values are
                       case insensitive. If omitted XmppFlask will try to
                       guest which one you have.
'''.lstrip() % dict(name=os.path.basename(sys.argv[0]))

_NO_APP = 'Target XmppFlask app is not specified. Try --help for more info.\n'


def run_server(app, jid, pwd, engine):
    if engine is None:
        try:
            return run_xmpppy_server(app, jid, pwd)
        except ImportError:
            try:
                return run_sleek_server(app, jid, pwd)
            except ImportError:
                raise RuntimeError('No suitable XMPP library available:'
                                   ' no xmpppy nor SleekXMPP')
    elif engine.lower() in ['xmpppy', 'xmpp']:
        return run_xmpppy_server(app, jid, pwd)
    elif engine.lower() in ['sleekxmpp', 'sleek']:
        return run_sleek_server(app, jid, pwd)
    else:
        raise ValueError('Unknown xmpp engine %s' % engine)


def run_xmpppy_server(app, jid, pwd):
    from .server.xmpppy import XmpppyWsgiServer
    server = XmpppyWsgiServer(app)
    server.connect(jid, pwd)
    server.serve_forever()
    return server


def run_sleek_server(app, jid, pwd):
    from .server.sleekxmpp import SleekXmppWsgiServer
    server = SleekXmppWsgiServer(app)
    server.connect(jid, pwd)
    server.serve_forever()
    return server


def main():
    def load_app_from_configstr(app_str):
        # TODO: There should be better way to load app
        path, app_varname = app_str.rsplit(u':', 1)
        path = os.path.abspath(path)
        if not os.path.exists(path):
            print u'Path %s does not exist' % path
            return
        if os.path.isdir(path):
            print u'Path %s is a directory' % path
            return
        dir_ = os.path.dirname(path)
        filename = os.path.basename(path)
        sys.path.insert(0, dir_)
        module = __import__(filename.rsplit('.py')[0])
        sys.path.pop(0)
        app = getattr(module, app_varname)
        return app

    jid = None
    password = None
    app = None
    engine = None

    try:
        options, arguments = getopt.gnu_getopt(
            sys.argv[1:], 'h',
            ['help', 'jid=', 'password=', 'engine=']
        )
    except getopt.GetoptError, err:
        sys.stdout.write(('%s\n\n' % err).capitalize())
        sys.stdout.write(_HELP)
        sys.stdout.flush()
        return 1

    for option, value in options:
        if option in ['--jid']:
            jid = value
        elif option in ['--password']:
            password = value
        elif option in ['--engine']:
            engine = value
        elif option in ['-h', '--help']:
            sys.stdout.write(_HELP)
            sys.stdout.flush()
            return 0

    if not arguments:
        sys.stdout.write(_NO_APP)
        sys.stdout.flush()
        sys.exit(1)

    app_path = arguments[0]

    if jid is None:
        if 'XMPPFLASK_JID' in os.environ:
            jid = os.environ['XMPPFLASK_JID']
        else:
            jid = raw_input(u'Enter XmppFlask bot JID: ')

    if password is None:
        if 'XMPPFLASK_PASSWORD' in os.environ:
            password = os.environ['XMPPFLASK_PASSWORD']
        else:
            password = getpass.getpass(u'Enter password for %s: ' % jid)

    app = load_app_from_configstr(app_path)
    if app is None:
        print 'Unable to load XmppFlask app %s' % app_path
        return 1

    try:
        run_server(app, jid, password, engine)
    except Exception as err:
        print '%s: %s' % (type(err).__name__, str(err))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
