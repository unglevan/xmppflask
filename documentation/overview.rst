========
Overview
========

Basic idea behind XmppFlask is being as simlpe as Flask is. So let's start from
a simple application.

.. code-block:: python

    # -*- coding: utf-8 -*-

    from xmppflask import XmppFlask
    app = XmppFlask(__name__)

    @app.route(u'ping')
    def ping():
        return u'pong'

-------
Routing
-------

Routing is pretty much the same as in Flask
`http://flask.pocoo.org/docs/quickstart/#routing <http://flask.pocoo.org/docs/quickstart/#routing>`_:

.. code-block:: python

    @app.route(u'ping <user> <int:n> times')
    def ping(user, n):
        return u'ponged %s %s times' % (user, n)

-------------------
Rendering Templates
-------------------

Take a look at http://flask.pocoo.org/docs/quickstart/#rendering-templates

.. code-block:: python

    @app.route(u'ping')
    def ping():
        return render_template(u'ping.html')

-------
Logging
-------

http://flask.pocoo.org/docs/quickstart/#logging

.. code-block:: python

    app.logger.debug('A value for debugging')
    app.logger.warning('A warning occurred (%d apples)', 42)
    app.logger.error('An error occurred')


--------
Sessions
--------

You may keep session context for each user that interacts with your app. Just
define session interface:

.. code-block:: python

    from xmppflask import XmppFlask
    from xmppflask.session import MemorySessionInterface
    from xmppflask import session

    app = XmppFlask(__name__)
    app.session_interface = MemorySessionInterface()

    @app.route(u'ping')
    def ping():
        if 'seq' not in session:
            session['seq'] = 0
        session['seq'] += 1
        return u"ping seq %d. PONG!" % session['seq']


--------
And more
--------

As in Flask you can do things like this:

.. code-block:: python

    @app.before_request
    def before_request():
        g.db = connect_db()

    @app.teardown_request
    def teardown_request(exception):
        g.db.close()

--------
XMPPWSGI
--------

In XmppFlask there's a thing called XMPPWSGI. Basically it's a "WSGI for XMPP"
(as you already might have guessed). To read about the whole WSGI idea you
can go and read `PEP 333 <http://www.python.org/dev/peps/pep-0333/>`_. In
XMPPWSGI, your application should be something like this (could be changed
in near time):

.. code-block:: python

   def xmppwsgi_app(self, environ, notification_queue):
       notification_queue.append(
           [('user1@gmail.com', 'notification 1'),
            ('user2@gmail.com', 'notification 2')])
       return u'response to user'

This code is a simple XMPPWSGI app that responses to user by string
"response to user" and also says to XMPPWSGI server to send messages
to user1@gmail.com and user2@gmail.com.

-------
Testing
-------

Just run ``nosetests`` inside environment.
