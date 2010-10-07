#!/usr/bin/env python

'''Tests for svn_merge.py'''

import unittest

import svn_merge

class SvnMergeTests(unittest.TestCase):

    log_output = '''<?xml version="1.0"?>
<log>
<logentry
   revision="18094">
<author>karen</author>
<date>2010-07-18T06:41:55.932156Z</date>
<msg>#5099 Change something
</msg>
</logentry>
</log>
'''

    def test_get_log_message(self):
        svn_merge.call = lambda cmd: self.log_output
        author, message = svn_merge.get_log_message('18094',
                'https://svnserver/svn/trunk')
        self.assertEqual(author, u'karen')
        self.assertEqual(message, u'#5099 Change something\n')

if __name__ == '__main__':
    unittest.main()
