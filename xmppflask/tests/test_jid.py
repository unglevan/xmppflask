# -*- coding: utf-8 -*-
"""
    xmppflask.test.test_jid
    ~~~~~~~~~~~~~~~~~~~~~~~

    Tests for JID wrapper.

    Part of SleekXMPP: The Sleek XMPP Library

    :copyright: (c) 2011 Nathanael C. Fritz
    :license: MIT, see LICENSE for more details
"""
from __future__ import unicode_literals
from xmppflask.tests.helpers import unittest
from xmppflask.jid import JID


class JIDTestCase(unittest.TestCase):
    """Verify that the JID class can parse and manipulate JIDs."""

    def check_jid(self, jid, user=None, domain=None, resource=None,
                  bare=None, full=None, string=None):
        """
        Verify the components of a JID.

        Arguments:
        jid -- The JID object to test.
        user -- Optional. The user name portion of the JID.
        domain -- Optional. The domain name portion of the JID.
        resource -- Optional. The resource portion of the JID.
        bare -- Optional. The bare JID.
        full -- Optional. The full JID.
        string -- Optional. The string version of the JID.
        """
        if user is not None:
            self.assertEqual(jid.user, user,
                             "User does not match: %s" % jid.user)
        if domain is not None:
            self.assertEqual(jid.domain, domain,
                             "Domain does not match: %s" % jid.domain)
        if resource is not None:
            self.assertEqual(jid.resource, resource,
                             "Resource does not match: %s" % jid.resource)
        if bare is not None:
            self.assertEqual(jid.bare, bare,
                             "Bare JID does not match: %s" % jid.bare)
        if full is not None:
            self.assertEqual(jid.full, full,
                             "Full JID does not match: %s" % jid.full)
        if string is not None:
            self.assertEqual(str(jid), string,
                             "String does not match: %s" % str(jid))

    def test_jid_from_full(self):
        """Test using JID of the form 'user@server/resource/with/slashes'."""
        self.check_jid(JID('user@someserver/some/resource'),
                       'user',
                       'someserver',
                       'some/resource',
                       'user@someserver',
                       'user@someserver/some/resource',
                       'user@someserver/some/resource')

    def test_jid_from_bare(self):
        """Test using JID of the form 'user@domain'."""
        self.check_jid(JID('user@domain'),
                       'user',
                       'domain',
                       '',
                       'user@domain',
                       'user@domain',
                       'user@domain')

    def test_jid_from_domain(self):
        """Test using JID of the form 'user@domain'."""
        self.check_jid(JID('domain'),
                       '',
                       'domain',
                       '',
                       'domain',
                       'domain',
                       'domain')

    def test_jid_from_domain_and_resource(self):
        """Test using JID of the form 'user@domain'."""
        self.check_jid(JID('domain/resource'),
                       '',
                       'domain',
                       'resource',
                       'domain',
                       'domain/resource',
                       'domain/resource')

    def test_jid_change(self):
        """Test changing JID of the form 'user@server/resource/with/slashes'"""
        j = JID('user1@someserver1/some1/resource1')
        j.user = 'user'
        j.domain = 'someserver'
        j.resource = 'some/resource'
        self.check_jid(j,
                       'user',
                       'someserver',
                       'some/resource',
                       'user@someserver',
                       'user@someserver/some/resource',
                       'user@someserver/some/resource')

    def test_get_jid_aliases(self):
        """Test JID aliases."""
        j = JID('user@someserver/resource')
        self.assertEqual(j.server, j.host)
        self.assertEqual(j.server, j.domain)
        self.assertEqual(j.user, j.node)
        self.assertEqual(j.full, j.jid)

    def test_set_jid_aliases(self):
        """Test changing JID using aliases for domain."""
        j = JID('user@someserver/resource')
        j.server = 'anotherserver'
        self.check_jid(j, domain='anotherserver')
        j.host = 'yetanother'
        self.check_jid(j, domain='yetanother')

    def test_jid_set_full_with_user(self):
        """Test setting the full JID with a user portion."""
        j = JID('user@domain/resource')
        j.full = 'otheruser@otherdomain/otherresource'
        self.check_jid(j,
                       'otheruser',
                       'otherdomain',
                       'otherresource',
                       'otheruser@otherdomain',
                       'otheruser@otherdomain/otherresource',
                       'otheruser@otherdomain/otherresource')

    def test_jid_full_no_user_with_resource(self):
        """
        Test setting the full JID without a user
        portion and with a resource.
        """
        j = JID('user@domain/resource')
        j.full = 'otherdomain/otherresource'
        self.check_jid(j,
                       '',
                       'otherdomain',
                       'otherresource',
                       'otherdomain',
                       'otherdomain/otherresource',
                       'otherdomain/otherresource')

    def test_jid_full_no_user_no_resource(self):
        """
        Test setting the full JID without a user
        portion and without a resource.
        """
        j = JID('user@domain/resource')
        j.full = 'otherdomain'
        self.check_jid(j,
                       '',
                       'otherdomain',
                       '',
                       'otherdomain',
                       'otherdomain',
                       'otherdomain')

    def test_jid_bare_user(self):
        """Test setting the bare JID with a user."""
        j = JID('user@domain/resource')
        j.bare = 'otheruser@otherdomain'
        self.check_jid(j,
                       'otheruser',
                       'otherdomain',
                       'resource',
                       'otheruser@otherdomain',
                       'otheruser@otherdomain/resource',
                       'otheruser@otherdomain/resource')

    def test_jid_bare_no_user(self):
        """Test setting the bare JID without a user."""
        j = JID('user@domain/resource')
        j.bare = 'otherdomain'
        self.check_jid(j,
                       '',
                       'otherdomain',
                       'resource',
                       'otherdomain',
                       'otherdomain/resource',
                       'otherdomain/resource')

    def test_jid_no_resource(self):
        """Test using JID of the form 'user@domain'."""
        self.check_jid(JID('user@someserver'),
                       'user',
                       'someserver',
                       '',
                       'user@someserver',
                       'user@someserver',
                       'user@someserver')

    def test_jid_no_user(self):
        """Test JID of the form 'component.domain.tld'."""
        self.check_jid(JID('component.someserver'),
                       '',
                       'component.someserver',
                       '',
                       'component.someserver',
                       'component.someserver',
                       'component.someserver')

    def test_jid_equality(self):
        """Test that JIDs with the same content are equal."""
        jid1 = JID('user@domain/resource')
        jid2 = JID('user@domain/resource')
        self.assertTrue(jid1 == jid2, "Same JIDs are not considered equal")
        self.assertFalse(jid1 != jid2, "Same JIDs are considered not equal")

    def test_jid_inequality(self):
        jid1 = JID('user@domain/resource')
        jid2 = JID('otheruser@domain/resource')
        self.assertFalse(jid1 == jid2, "Same JIDs are not considered equal")
        self.assertTrue(jid1 != jid2, "Same JIDs are considered not equal")

