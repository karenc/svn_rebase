#!/usr/bin/env python

'''Tests for svn_rebase.py
'''

import unittest

import svn_rebase

class TestSvnMultiMerge(unittest.TestCase):
    def test_parse_revisions(self):
        self.assertEqual(
                svn_rebase.parse_revisions(
                    '1000-1005,1008,1010-1012,1015,1020'),
                [1000, 1001, 1002, 1003, 1004, 1005,
                    1008, 1010, 1011, 1012, 1015, 1020])

    def test_get_source_revisions(self):
        svn_rebase._get_source_revisions = lambda source, stop_on_copy: (
                '''<?xml version="1.0"?>
<log>
<logentry
   revision="6643">
<author>karen</author>
<date>2010-07-27T11:14:29.911990Z</date>
<msg>svn merge tool
</msg>
</logentry>
<logentry
   revision="6583">
<author>karen</author>
<date>2010-07-21T20:39:32.503726Z</date>
<msg>Add script to go back one version at a time
</msg>
</logentry>
<logentry
   revision="6546">
<author>karen</author>
<date>2010-07-19T10:02:56.791878Z</date>
<msg>Helper script for svn merging
</msg>
</logentry>
</log>

                         ''')
        self.assertEqual(svn_rebase.get_source_revisions('source'),
                [6643, 6583, 6546])

    def test_save_load_state(self):
        svn_rebase.save_state(
                'https://svn_server/path',
                [1, 2, 3],
                None)
        self.assertEqual(svn_rebase.load_state(), {
            'source': 'https://svn_server/path',
            'revisions': [1, 2, 3],
            'destination': None,
            })

    def test_load_state_non_existent(self):
        self.assertEqual(svn_rebase.load_state(), None)

if __name__ == '__main__':
    unittest.main()
