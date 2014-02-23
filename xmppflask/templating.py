# -*- coding: utf-8 -*-
"""
    xmppflask.templating
    ~~~~~~~~~~~~~~~~~~~~

    Implements the bridge to Jinja2.

    :copyright: (c) 2014 Kostyantyn Rybnikov <k.bx@ya.ru>
    :license: BSD
"""

import posixpath

from jinja2 import (
    BaseLoader, Environment as BaseEnvironment, TemplateNotFound
)

from .globals import _app_ctx_stack, _request_ctx_stack


def _default_template_ctx_processor():
    """Default template context processor.  Injects `request`, and `g`.
    """
    reqctx = _request_ctx_stack.top
    appctx = _app_ctx_stack.top
    rv = {}
    if appctx is not None:
        rv['g'] = appctx.g
    if reqctx is not None:
        rv['request'] = reqctx.request
        rv['session'] = reqctx.session
    return rv


class Environment(BaseEnvironment):

    def __init__(self, app, **options):
        if 'loader' not in options:
            options['loader'] = app.create_global_jinja_loader()
        BaseEnvironment.__init__(self, **options)
        self.app = app


class DispatchingJinjaLoader(BaseLoader):
    """A loader that looks for templates in the application and all
    the blueprint folders.
    """

    def __init__(self, app):
        self.app = app

    def get_source(self, environment, template):
        for loader, local_name in self._iter_loaders(template):
            try:
                return loader.get_source(environment, local_name)
            except TemplateNotFound:
                pass

        raise TemplateNotFound(template)

    def _iter_loaders(self, template):
        loader = self.app.jinja_loader
        if loader is not None:
            yield loader, template

        # old style module based loaders in case we are dealing with a
        # blueprint that is an old style module
        try:
            module, local_name = posixpath.normpath(template).split('/', 1)
            blueprint = self.app.blueprints[module]
        except (ValueError, KeyError):
            pass

        for blueprint in self.app.blueprints.itervalues():
            loader = blueprint.jinja_loader
            if loader is not None:
                yield loader, template

    def list_templates(self):
        result = set()
        loader = self.app.jinja_loader
        if loader is not None:
            result.update(loader.list_templates())

        for name, blueprint in self.app.blueprints.iteritems():
            loader = blueprint.jinja_loader
            if loader is not None:
                for template in loader.list_templates():
                    prefix = ''
                    result.add(prefix + template)

        return list(result)


def _render(template, context, app):
    """Renders the template and fires the signal"""
    rv = template.render(context)
    return rv


def render_template(template_name, **context):
    """Renders a template from the template folder with the given
    context.

    :param template_name: the name of the template to be rendered
    :param context: the variables that should be available in the
                    context of the template.
    """
    ctx = _app_ctx_stack.top
    ctx.app.update_template_context(context)
    return _render(ctx.app.jinja_env.get_template(template_name),
                   context, ctx.app)


def render_template_string(source, **context):
    """Renders a template from the given template source string
    with the given context.

    :param template_name: the sourcecode of the template to be
                          rendered
    :param context: the variables that should be available in the
                    context of the template.
    """
    ctx = _app_ctx_stack.top
    ctx.app.update_template_context(context)
    return _render(ctx.app.jinja_env.from_string(source),
                   context, ctx.app)
