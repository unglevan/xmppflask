# -*- coding: utf-8 -*-
"""
    xmppflask.routing
    ~~~~~~~~~~~~~~~~~

    :copyright: (c) 2014 Kostyantyn Rybnikov <k.bx@ya.ru>
    :license: BSD
"""

import re
from itertools import izip

from .exceptions import NotFound
from .thirdparty.werkzeug import ImmutableDict, MultiDict
from .thirdparty.werkzeug import get_converter, parse_rule


class BuildError(Exception):
    pass


class BaseConverter(object):
    """Base class for all converters."""
    regex = '.*+'
    is_greedy = False
    weight = 100

    def __init__(self, map_):
        self.map = map_
        super(BaseConverter, self).__init__()

    def to_python(self, value):
        return value

    def to_message(self, value):
        return unicode(value)


class UnicodeConverter(BaseConverter):
    """This converter is the default converter and accepts any string.

    This is the default validator.

    Example::

        Rule('/pages/<page>'),
        Rule('/<string(length=2):lang_code>')

    :param map_: the :class:`Map`.
    :param minlength: the minimum length of the string.  Must be greater
                      or equal 1.
    :param maxlength: the maximum length of the string.
    :param length: the exact length of the string.
    """

    regex = '.'

    def __init__(self, map_, minlength=1, maxlength=None, length=None):
        super(UnicodeConverter, self).__init__(map)
        if length is not None:
            length = '{%d}' % int(length)
        else:
            if maxlength is None:
                maxlength = ''
            else:
                maxlength = int(maxlength)
            length = '{%s,%s}' % (
                int(minlength),
                maxlength
            )
        self.regex += length


class UnicodeWordConverter(UnicodeConverter):
    regex = r'\S'


class AnyConverter(BaseConverter):
    """Matches one of the items provided.  Items can either be Python
    identifiers or unicode strings::

        Rule('/<any(about, help, imprint, u"class"):page_name>')

    :param map_: the :class:`Map`.
    :param items: this function accepts the possible items as positional
                  arguments.
    """

    def __init__(self, map_, *items):
        super(AnyConverter, self).__init__(map_)
        self.regex = '(?:%s)' % '|'.join([re.escape(x) for x in items])


class NumberConverter(BaseConverter):
    """Baseclass for `IntegerConverter` and `FloatConverter`.

    :internal:
    """

    def __init__(self, map_, fixed_digits=0, min_=None, max_=None):
        super(NumberConverter, self).__init__(map_)
        self.fixed_digits = fixed_digits
        self.min = min_
        self.max = max_

    def to_python(self, value):
        if self.fixed_digits and len(value) != self.fixed_digits:
            raise ValidationError()
        value = self.num_convert(value)
        if (self.min is not None and value < self.min) or \
                (self.max is not None and value > self.max):
            raise ValidationError()
        return value

    def to_message(self, value):
        value = self.num_convert(value)
        if self.fixed_digits:
            value = (u'%%0%sd' % self.fixed_digits) % value
        return value

    def num_convert(self, value):
        raise NotImplementedError


class IntegerConverter(NumberConverter):
    """This converter only accepts integer values::

        Rule('/page/<int:page>')

    This converter does not support negative values.

    :param map: the :class:`Map`.
    :param fixed_digits: the number of fixed digits in the URL.  If you set
                         this to ``4`` for example, the application will
                         only match if the url looks like ``/0001/``.  The
                         default is variable length.
    :param min: the minimal value.
    :param max: the maximal value.
    """
    regex = r'\d+'
    num_convert = int


class FloatConverter(NumberConverter):
    """This converter only accepts floating point values::

        Rule('/probability/<float:probability>')

    This converter does not support negative values.

    :param map: the :class:`Map`.
    :param min: the minimal value.
    :param max: the maximal value.
    """
    regex = r'\d+\.\d+'
    num_convert = float

    def __init__(self, map_, min_=None, max_=None):
        super(FloatConverter, self).__init__(map_, 0, min_, max_)


#: the default converter mapping for the map.
DEFAULT_CONVERTERS = {
    'default': UnicodeWordConverter,
    'string': UnicodeConverter,
    'any': AnyConverter,
    'int': IntegerConverter,
    'float': FloatConverter
}


class ValidationError(ValueError):
    pass


class Rule(object):
    """Rule to handle single message"""

    def __init__(self, string=None, defaults=None, endpoint=None,
                 event_type=None, from_jid=None, type=None, redirect_to=None,
                 strict=True):
        self.rule = string or ''
        self.map = None
        self.defaults = defaults
        self.endpoint = endpoint
        self.event_type = event_type
        self.from_jid = from_jid
        self.type = type
        self.greediness = 0
        self.redirect_to = redirect_to
        self.strict = strict

        self._trace = None
        self._weights = None
        self._converters = None
        self._regex = None

        if defaults is not None:
            self.arguments = set(map(str, defaults))
        else:
            self.arguments = set()

    def get_rules(self, map_):
        yield self

    def bind(self, map_, rebind=False):
        """Bind the route to a map and create a regular expression based on
        the information from the rule itself and the defaults from the map.

        :internal:
        """
        if self.map is not None and not rebind:
            raise RuntimeError('route %r already bound to map %r' %
                               (self, self.map))
        self.map = map_
        rule = self.rule

        self._trace = []
        self._converters = {}
        self._weights = []

        regex_parts = []
        for converter, arguments, variable in parse_rule(rule):
            if converter is None:
                regex_parts.append(re.escape(variable))
                self._trace.append((False, variable))
                self._weights.append(len(variable))
            else:
                convobj = get_converter(map_, converter, arguments)
                regex_parts.append('(?P<%s>%s)' % (variable, convobj.regex))
                self._converters[variable] = convobj
                self._trace.append((True, variable))
                self._weights.append(convobj.weight)
                self.arguments.add(str(variable))
                if convobj.is_greedy:
                    self.greediness += 1

        regex = u''.join(regex_parts)
        if self.strict:
            regex = '^' + regex + '$'
        self._regex = re.compile(regex, re.UNICODE)

    def match(self, message, event_type, from_jid, type):
        """Check if rule matches a given message"""
        if self.event_type is not None and event_type is not None:
            if self.event_type != event_type:
                return

        if self.type is not None and type is not None:
            if self.type != type:
                return

        if self.from_jid is not None and from_jid is not None:
            if not re.match(self.from_jid, from_jid):
                return

        m = self._regex.search(message)
        if m is not None:
            groups = m.groupdict()
            result = {}
            for name, value in groups.iteritems():
                try:
                    value = self._converters[name].to_message(value)
                except ValidationError:
                    return
                result[str(name)] = value
            if self.defaults is not None:
                result.update(self.defaults)
            return result

    def build(self, values):
        """
        :internal:
        """
        tmp = []
        add = tmp.append
        for is_dynamic, data in self._trace:
            if is_dynamic:
                try:
                    add(self._converters[data].to_python(values[data]))
                except ValidationError:
                    return
            else:
                add(data)
        url = u''.join(unicode(x) for x in tmp)

        return url

    def suitable_for(self, values):
        """Check if the dict of values has enough data for url generation

        :internal:
        """
        valueset = set(values)

        for key in self.arguments - set(self.defaults or ()):
            if key not in values:
                return False

        if self.arguments.issubset(valueset):
            if self.defaults is None:
                return True
            for key, value in self.defaults.iteritems():
                if value != values[key]:
                    return False

        return True

    def __repr__(self):
        if self.map is None:
            return u'<%s (unbound)>' % self.__class__.__name__
        tmp = []
        for is_dynamic, data in self._trace:
            if is_dynamic:
                tmp.append(u'<%s>' % data)
            else:
                tmp.append(data)
        return u'<%s %s -> %s>' % (
            self.__class__.__name__,
            u''.join(tmp),
            self.endpoint
        )

    def match_compare(self, other):
        """Compare this object with another one for matching.
        Needed to match "hello world" rule before "hello" rule ("hello"
        must be later in search/match order).

        :internal:
        """
        for sw, ow in izip(self._weights, other._weights):
            if sw > ow:
                return -1
            elif sw < ow:
                return 1
        if len(self._weights) > len(other._weights):
            return -1
        if len(self._weights) < len(other._weights):
            return 1
        if not other.arguments and self.arguments:
            return 1
        elif other.arguments and not self.arguments:
            return -1
        elif other.defaults is None and self.defaults is not None:
            return 1
        elif other.defaults is not None and self.defaults is None:
            return -1
        elif self.greediness > other.greediness:
            return -1
        elif self.greediness < other.greediness:
            return 1
        elif len(self.arguments) > len(other.arguments):
            return 1
        elif len(self.arguments) < len(other.arguments):
            return -1
        return 1

    def build_compare(self, other):
        return self.match_compare(other) # not sure if that's right


class Map(object):
    """Map of routes and their handlers"""

    #: for more on converters see http://werkzeug.pocoo.org/docs/routing/
    default_converters = ImmutableDict(DEFAULT_CONVERTERS)

    def __init__(self, rules=None, converters=None):
        self._rules = []
        self._rules_by_endpoint = {}
        self._remap = True

        self.converters = self.default_converters.copy()
        if converters:
            self.converters.update(converters)
        for rulefactory in rules or ():
            self.add(rulefactory)

    def add(self, rulefactory):
        """Add a new rule to the map and bind it.

        :param rule: a :class:`Rule`
        """
        for rule in rulefactory.get_rules(self):
            rule.bind(self)
            self._rules.append(rule)
            (self._rules_by_endpoint
             .setdefault(rule.endpoint, [])
             .append(rule))
        self._remap = True

    def bind(self, message=None, event_type=None, from_jid=None, type=None):
        return MapAdapter(self, message=message,
                          event_type=event_type, from_jid=from_jid, type=type)

    def bind_to_environ(self, environ):
        return self.bind(event_type=environ.get('xmpp.stanza'),
                         from_jid=environ['xmpp.jid'],
                         message=environ.get('xmpp.body', ''),
                         type=environ.get('xmpp.stanza_type'))

    def update(self):
        if self._remap:
            self._rules.sort(lambda a, b: a.match_compare(b))
            for rules in self._rules_by_endpoint.itervalues():
                rules.sort(lambda a, b: a.match_compare(b))
            self._remap = False


class MapAdapter(object):
    def __init__(self, map_,
                 message=None, event_type=None, from_jid=None, type=None):
        self.message = message or u''
        self.event_type = event_type
        self.from_jid = from_jid
        self.type = type
        self.map = map_

    def match(self, message=None, return_rule=False,
              event_type=None, from_jid=None, type=None):
        """The actual match func that is used to get endpoint (or rule) and
        parameters to call (or use somehow).
        """
        # TODO: redirects maybe
        self.map.update()
        message = message or self.message
        event_type = event_type or self.event_type
        from_jid = from_jid or self.from_jid
        type = type or self.type
        for rule in self.map._rules:
            rv = rule.match(message=message,
                            event_type=event_type,
                            from_jid=str(from_jid),
                            type=type)
            if rv is None:
                continue
            if return_rule:
                return rule, rv
            else:
                return rule.endpoint, rv
        raise NotFound()

    def build(self, endpoint, values=None):
        """Building messages that suite certain endpoint with valutes (params).

        In XMPP world it might be not as must-have feature, but still it's
        needed and nice.
        """
        self.map.update()
        if values:
            if isinstance(values, MultiDict):
                values = dict((k, v) for k, v in values.iteritems(multi=True)
                              if v is not None)
            else:
                values = dict((k, v) for k, v in values.iteritems()
                              if v is not None)
        else:
            values = {}

        rv = self._partial_build(endpoint, values)
        if rv is None:
            raise BuildError(endpoint, values)
        message = rv

        return message

    def _partial_build(self, endpoint, values):
        for rule in self.map._rules_by_endpoint.get(endpoint, ()):
            if rule.suitable_for(values):
                rv = rule.build(values)
                if rv is not None:
                    return rv
