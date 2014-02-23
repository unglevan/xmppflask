# -*- coding: utf-8 -*-

from xmppflask.tests.helpers import unittest
from xmppflask.helpers import get_package_path


class TestHelpers(unittest.TestCase):

    def test_no_package_path(self):
        import os

        self.assertEquals(get_package_path('no_such_package(i_hope)'),
                          os.getcwd())

    def test_safe_join(self):
        from xmppflask import safe_join
        from xmppflask.exceptions import NotFound

        self.assertEquals(safe_join('a', 'b'),
                          'a/b')
        self.assertRaises(NotFound,
                          lambda: safe_join('a', '../b'))

