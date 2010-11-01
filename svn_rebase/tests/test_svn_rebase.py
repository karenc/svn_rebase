#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''Tests for svn_rebase.py
'''

import StringIO
import unittest

import mock

import svn_rebase


class TestSvnRebase(unittest.TestCase):
    # save these variables in svn_rebase and restore them in tear down
    save_and_restore = [
            'call',
            'load_state',
            'optparse',
            'os',
            'remove_state_file',
            'svn_rebase',
            'sys',
            ]
    def setUp(self):
        for var in self.save_and_restore:
            setattr(self, var, getattr(svn_rebase, var))

        self.options = mock.Mock()
        self.options.revisions = None
        self.options.abort = None
        self.options.destination = None
        self.options.cont = None
        self.args = []

    def tearDown(self):
        for var in self.save_and_restore:
            setattr(svn_rebase, var, getattr(self, var))
        self.read_interactive_teardown()

    def test_get_log_message(self):
        log_output = '''<?xml version="1.0"?>
<log>
<logentry
   revision="18094">
<author>karen</author>
<date>2010-07-18T06:41:55.932156Z</date>
<msg>#5099 Change これ
</msg>
</logentry>
</log>
'''
        svn_rebase.call = lambda cmd: log_output
        author, message = svn_rebase.get_log_message('18094',
                'https://svnserver/svn/trunk')
        self.assertEqual(author, u'karen')
        self.assertEqual(message, u'#5099 Change これ\n')

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
        self.assertEqual(svn_rebase.get_source_revisions('source'), [
            {'revision': 6643, 'msg': 'svn merge tool\n'},
            {'revision': 6583,
                'msg': 'Add script to go back one version at a time\n'},
            {'revision': 6546, 'msg': 'Helper script for svn merging\n'},
            ])

    def test_save_load_state(self):
        svn_rebase.save_state(
                'https://svn_server/path',
                revisions=[1, 2, 3],
                destination=None,
                auto_commit=False)
        self.assertEqual(svn_rebase.load_state(), {
            'source': 'https://svn_server/path',
            'revisions': [1, 2, 3],
            'destination': None,
            'auto_commit': False,
            })

    def test_load_state_non_existent(self):
        self.assertEqual(svn_rebase.load_state(), None)

    def read_interactive_teardown(self):
        svn_rebase.open = open

    def test_read_interactive_comments(self):
        open_ = {
                svn_rebase.INTERACTIVE_FILENAME: StringIO.StringIO('''
# comment
 # ...
   '''),
                }
        svn_rebase.open = mock.Mock(side_effect=open_.get)
        svn_rebase.os = mock.Mock()
        revisions, commands = svn_rebase.read_interactive([1000])
        self.assert_(svn_rebase.open.called)
        self.assertEqual(revisions, [])
        self.assertEqual(commands, {})

    def test_read_interactive_no_revision(self):
        open_ = {
                svn_rebase.INTERACTIVE_FILENAME: StringIO.StringIO('edit\n'),
                }
        svn_rebase.open = mock.Mock(side_effect=open_.get)
        self.assertRaises(svn_rebase.InvalidInteractiveFile,
            svn_rebase.read_interactive,
            [1000])

    def test_read_interactive_invalid_revision(self):
        open_ = {
                svn_rebase.INTERACTIVE_FILENAME: StringIO.StringIO('edit x123\n'),
                }
        svn_rebase.open = mock.Mock(side_effect=open_.get)
        self.assertRaises(svn_rebase.InvalidInteractiveFile,
                svn_rebase.read_interactive,
                [1000])

        open_ = {
                svn_rebase.INTERACTIVE_FILENAME: StringIO.StringIO('edit 123\n'),
                }
        svn_rebase.open = mock.Mock(side_effect=open_.get)
        self.assertRaises(svn_rebase.InvalidInteractiveFile,
                svn_rebase.read_interactive,
                [1000])

    def test_read_interactive_first_squash(self):
        open_ = {
                svn_rebase.INTERACTIVE_FILENAME: StringIO.StringIO(
                    'squash 1000 some stuff'),
                }
        svn_rebase.open = mock.Mock(side_effect=open_.get)
        self.assertRaises(svn_rebase.InvalidInteractiveFile,
                svn_rebase.read_interactive,
                [1000])

    def test_read_interactive_normal(self):
        open_ = {
                svn_rebase.INTERACTIVE_FILENAME: StringIO.StringIO(
                    'edit 1000 comments\n'
                    's 999 blah\n'
                    'pick 1001\n'
                    'p 1003\n'
                    'squash 1004 テスト\n'
                    ),
                }
        svn_rebase.open = mock.Mock(side_effect=open_.get)
        svn_rebase.os = mock.Mock()
        revisions, commands = svn_rebase.read_interactive([999,
            1000, 1001, 1002, 1003, 1004])
        self.assertEqual(revisions, [[1000, 999], [1001], [1003, 1004]])
        self.assertEqual(commands, {
            1000: 'e',
            1001: 'p',
            1003: 'p',
            })
        self.assertEqual(svn_rebase.os.remove.call_count, 1)

    def main_setup(self):
        svn_rebase.sys = mock.Mock()
        def sys_exit(*args):
            raise SystemExit
        svn_rebase.sys.exit.side_effect = sys_exit
        svn_rebase.svn_rebase = mock.Mock()
        svn_rebase.load_state = mock.Mock()
        svn_rebase.optparse = mock.Mock()
        svn_rebase.remove_state_file = mock.Mock()

        parser = mock.Mock()
        parser.error.side_effect = sys_exit
        svn_rebase.optparse.OptionParser.return_value = parser
        parser.parse_args.return_value = self.options, self.args

    def test_main_empty(self):
        self.main_setup()
        svn_rebase.sys.argv = ['svn_rebase', '']
        try:
            svn_rebase.main()
        except SystemExit:
            pass
        self.assertFalse(svn_rebase.svn_rebase.called)

    def test_main_continue(self):
        self.main_setup()
        svn_rebase.load_state.return_value = {
                'source': 'http://nohost/svn/',
                }
        self.options.cont = True
        svn_rebase.sys.argv = ['svn_rebase', '-c']
        svn_rebase.main()

        self.assertTrue(svn_rebase.svn_rebase.called)
        self.assertEqual(svn_rebase.svn_rebase.call_args[1],
                {'source': 'http://nohost/svn/'})

    def test_main_continue_without_saved_state(self):
        self.main_setup()
        svn_rebase.load_state.return_value = None
        self.options.cont = True
        svn_rebase.sys.argv = ['svn_rebase', '-c']
        try:
            svn_rebase.main()
        except SystemExit:
            pass
        self.assertFalse(svn_rebase.svn_rebase.called)

    def test_main_continue_with_other_args(self):
        self.main_setup()
        self.options.cont = True
        self.options.abort = True
        svn_rebase.sys.argv = ['svn_rebase', '-c', '-a']
        try:
            svn_rebase.main()
        except SystemExit:
            pass
        self.assertFalse(svn_rebase.svn_rebase.called)

    def test_main_abort(self):
        self.main_setup()
        self.options.abort = True
        svn_rebase.sys.argv = ['svn_rebase', '-a']
        try:
            svn_rebase.main()
        except SystemExit:
            pass
        self.assertTrue(svn_rebase.remove_state_file.called)
        self.assertFalse(svn_rebase.svn_rebase.called)

    def test_main_abort_with_other_args(self):
        self.main_setup()
        self.options.abort = True
        self.options.revisions = '123'
        svn_rebase.sys.argv = ['svn_rebase', '-c', '-r123']
        try:
            svn_rebase.main()
        except SystemExit:
            pass
        self.assertFalse(svn_rebase.remove_state_file.called)
        self.assertFalse(svn_rebase.svn_rebase.called)

    def test_main(self):
        self.args = ['http://nohost/svn/']
        self.options.revisions = '1234'
        self.options.destination = 'src'
        self.options.auto_commit = False
        self.main_setup()
        svn_rebase.sys.argv = ['svn_rebase', 'http://nohost/svn/']
        svn_rebase.main()
        self.assertTrue(svn_rebase.svn_rebase.called)
        self.assertTrue(svn_rebase.svn_rebase.call_args[1], {
            'source': 'http://nohost/svn/',
            'revisions': '1234',
            'destination': 'src',
            'auto_commit': False,
            })


if __name__ == '__main__':
    unittest.main()
