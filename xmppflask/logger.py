# -*- coding: utf-8 -*-
"""
    xmppflask.logger
    ~~~~~~~~~~~~~~~~

    Local version of flask.logging module.
    Implements the logging support for XmppFlask.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD
"""

from __future__ import absolute_import

from logging import getLogger, StreamHandler, Formatter, getLoggerClass, DEBUG


def create_logger(app):
    """Creates a logger for the given application.  This logger works
    similar to a regular Python logger but changes the effective logging
    level based on the application's debug flag.  Furthermore this
    function also removes all attached handlers in case there was a
    logger with the log name before.
    """
    Logger = getLoggerClass()

    class DebugLogger(Logger):
        def getEffectiveLevel(x):
            return DEBUG if app.debug else Logger.getEffectiveLevel(x)

    class DebugHandler(StreamHandler):
        def emit(x, record):
            StreamHandler.emit(x, record) if app.debug else None

    handler = DebugHandler()
    handler.setLevel(DEBUG)
    handler.setFormatter(Formatter(app.debug_log_format))
    logger = getLogger(app.logger_name)
    # just in case that was not a new logger, get rid of all the handlers
    # already attached to it.
    del logger.handlers[:]
    logger.__class__ = DebugLogger
    logger.addHandler(handler)
    return logger
