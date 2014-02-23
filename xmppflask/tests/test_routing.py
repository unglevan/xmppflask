# -*- coding: utf-8 -*-
"""
    xmppflask.routing test
    ~~~~~~~~~~~~~~~~~~~~~~

    :copyright: (c) 2011 Kostyantyn Rybnikov <k.bx@ya.ru>
    :license: BSD
"""

from xmppflask.tests.helpers import unittest

from xmppflask.routing import Map, Rule
from xmppflask.exceptions import NotFound


class RoutingFunctionality(unittest.TestCase):

    def test_simple(self):
        map_ = Map([
            Rule(u'ping', endpoint='ping'),
            Rule(u'ping me', endpoint='ping_me'),
            Rule(u'pong', endpoint='pong'),
            Rule('weather in <string(maxlength=10):city>',
                 endpoint='weather_in_city'),
            Rule('weather in country <string(length=2):country_code>',
                 endpoint='weather_in_country'),
        ])
        adapter = map_.bind()
        self.assertEquals(adapter.match('ping'), ('ping', {}))
        self.assertEquals(adapter.match('ping me'), ('ping_me', {}))
        self.assertEquals(adapter.match('pong'), ('pong', {}))
        self.assertEquals(adapter.match('weather in Kiev'),
                          ('weather_in_city', {'city': 'Kiev'}))
        self.assertEquals(adapter.match('weather in country UA'),
                          ('weather_in_country', {'country_code': 'UA'}))

    def test_basic_building(self):
        map_ = Map([
            Rule('ping', endpoint='ping'),
            Rule('ping <user>', endpoint='ping_user'),
            Rule('ping <user> <int:n> times',
                 endpoint='ping_user_multiple_times'),
        ])
        adapter = map_.bind()

        self.assertEquals(adapter.build('ping', {}),
                          'ping')
        self.assertEquals(adapter.build('ping_user', {'user': 'k_bx'}),
                          'ping k_bx')
        self.assertEquals(
            adapter.build('ping_user_multiple_times', {'user': 'k_bx',
                                                       'n': 5}),
            'ping k_bx 5 times')

    def test_defaults(self):
        map_ = Map([
            Rule('ping', defaults={'user': 'k_bx'}, endpoint='ping'),
            Rule('ping <int:n> times', endpoint='ping_n_times')
        ])
        adapter = map_.bind()

        self.assertEquals(adapter.match('ping'),
                          ('ping', {'user': 'k_bx'}))
        self.assertEquals(adapter.match('ping 7 times'),
                          ('ping_n_times', {'n': 7}))

        self.assertEquals(adapter.build('ping'), 'ping')

    def test_rule_repr_simple(self):
        rule = Rule('ping')
        self.assertEquals(repr(rule),
                          '<Rule (unbound)>')

    def test_rule_repr_binded(self):
        map_ = Map([
            Rule('ping <user> <int:n> times', endpoint='ping')
        ])
        self.assertEquals(
            repr(map_._rules[0]),
            '<Rule ping <user> <n> times -> ping>')

    def test_any_converter(self):
        map_ = Map([
            Rule('ping <any(u"k_bx", u"kb", u"kost-bebix"):user>',
                 endpoint='ping')
        ])
        adapter = map_.bind()
        self.assertEquals(adapter.match('ping k_bx'),
                          ('ping', {'user': 'k_bx'}))

    def test_suitable_for(self):
        map_ = Map([
            Rule('ping <any(u"k_bx", u"kb", u"kost-bebix"):user>',
                 endpoint='ping'),
            Rule('ping some <chicken> and <rabbit>',
                 endpoint='ping_some_chicken_and_rabbit',
                 defaults={'chicken': 'Chicken John'})
        ])
        rule = map_._rules[0]
        rule_2 = map_._rules[1]
        self.assertEquals(rule.suitable_for({'user': 'kb'}),
                          True)
        self.assertEquals(rule.suitable_for({}),
                          False)
        self.assertEquals(rule_2.suitable_for({}),
                          False)
        self.assertEquals(rule_2.suitable_for({'rabbit': 'Rabbit Jack'}),
                          True)
        self.assertEquals(rule_2.suitable_for({'rabbit': 'Rabbit Jack',
                                               'chicken': 'Chicken John'}),
                          True)
        self.assertEquals(rule_2.suitable_for({'rabbit': 'Rabbit Jack',
                                               'chicken': 'Chicken Joe'}),
                          False)

    def test_aliases(self):
        def ping():
            return 'pong'

        rmap = Map()
        rmap.add(Rule('ping', endpoint=ping))
        rmap.add(Rule('pong', endpoint=ping))
        rmap.update()

    def test_route_filtered_by_event_type(self):
        rmap = Map()
        rmap.add(Rule('ping', event_type='foo', endpoint='ping'))
        rmap.add(Rule('pong', event_type='bar', endpoint='pong'))

        adapter = rmap.bind()
        self.assertEqual(adapter.match('ping', event_type='foo'), ('ping', {}))
        self.assertEqual(adapter.match('pong', event_type='bar'), ('pong', {}))

        self.assertRaises(NotFound, adapter.match, 'pong', event_type='foo')
        self.assertRaises(NotFound, adapter.match, 'ping', event_type='bar')

    def test_route_filtered_by_type(self):
        rmap = Map()
        rmap.add(Rule('ping', type='foo', endpoint='ping'))
        rmap.add(Rule('pong', type='bar', endpoint='pong'))

        adapter = rmap.bind()
        self.assertEqual(adapter.match('ping', type='foo'), ('ping', {}))
        self.assertEqual(adapter.match('pong', type='bar'), ('pong', {}))

        self.assertRaises(NotFound, adapter.match, 'pong', type='foo')
        self.assertRaises(NotFound, adapter.match, 'ping', type='bar')

    def test_route_filtered_by_sender_jid(self):
        rmap = Map()
        rmap.add(Rule('ping', from_jid='.*@xmpp.ru', endpoint='ping'))
        rmap.add(Rule('pong', from_jid='foo@bar', endpoint='pong'))

        adapter = rmap.bind()
        self.assertEqual(
            adapter.match('ping', from_jid='foo@xmpp.ru'),
            ('ping', {}))
        self.assertEqual(
            adapter.match('ping', from_jid='bar@xmpp.ru'),
            ('ping', {}))
        self.assertEqual(
            adapter.match('pong', from_jid='foo@bar'),
            ('pong', {}))
        self.assertEqual(
            adapter.match('pong', from_jid='foo@bar.ru'),
            ('pong', {}))

        self.assertRaises(NotFound, adapter.match, 'ping', from_jid='foo@bar')
        self.assertRaises(NotFound, adapter.match, 'ping', from_jid='bar')
        self.assertRaises(NotFound, adapter.match, 'ping', from_jid='bar@foo')
        self.assertRaises(NotFound, adapter.match, 'pong',
                          from_jid='foo@xmpp.ru')
        self.assertRaises(NotFound, adapter.match, 'pong', from_jid='_foo@bar')

    def test_default_word_converter(self):
        rmap = Map()
        rmap.add(Rule('ping <host>', endpoint='ping'))

        adapter = rmap.bind()
        self.assertEqual(adapter.match('ping foo'), ('ping', {'host': 'foo'}))
        self.assertRaises(NotFound, adapter.match, 'ping foo bar')

    def test_string_converter(self):
        rmap = Map()
        rmap.add(Rule('ping <string:host>', endpoint='ping'))

        adapter = rmap.bind()
        self.assertEqual(adapter.match('ping foo'), ('ping', {'host': 'foo'}))
        self.assertEqual(adapter.match('ping foo bar'),
                         ('ping', {'host': 'foo bar'}))

    def test_diff_of_strict_and_non_strict_rules(self):
        rmap = Map()
        rmap.add(Rule('ping <host>', endpoint='ping'))
        rmap.add(Rule('pong <host>', endpoint='pong', strict=False))

        adapter = rmap.bind()
        self.assertEqual(adapter.match('ping example.com.'),
                         ('ping', {'host': 'example.com.'}))
        self.assertRaises(NotFound, adapter.match, 'ping foo bar')

        self.assertEqual(adapter.match('pong example.com.'),
                         ('pong', {'host': 'example.com.'}))
        self.assertEqual(adapter.match('pong foo tail'),
                         ('pong', {'host': 'foo'}))
