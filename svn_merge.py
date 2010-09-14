#!/usr/bin/env python

'''This script merges in changes from a changeset and then add a file called
svn_commit.  When executed like this:
. svn_commit
it will include the original commit message in vim for the user to edit.
'''

import os
import subprocess
import sys
import re

from lxml import etree

class CallError(Exception):
    pass

def call(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise CallError
    return stdout

def get_log_message(revision, source):
    results = call(['svn', 'log', '--xml', '-r', revision, source])
    root = etree.fromstring(results)
    return (unicode(root.xpath('/log/logentry/author/text()')[0]),
        unicode(root.xpath('/log/logentry/msg/text()')[0]))

def svn_merge(source, revision, destination=None, auto_commit=False):
    call_args = ['svn', 'merge', '--accept', 'postpone', '-c', revision, source]
    if destination is not None:
        call_args.append(destination)
    call(call_args)
    filename = 'r%s_commit_message' % revision
    author, message = get_log_message(revision, source)
    message = message.strip()
    f = open(filename, 'w')
    f.write(message)
    if not re.search('\(([^ ]* )?merge r[^)]*\)$', message):
        f.write(' (%s, merge r%s)' % (author, revision))
    f.close()
    if auto_commit:
        call(['svn', 'commit', '-F', filename])
        os.remove(filename)
        return message
    f = open('svn_commit', 'w')
    f.write('svn commit --editor-cmd "vim +\'r %s\'"\n' % filename)
    f.write('rm -f %s\n' % filename)
    f.close()
    print 'Please use this command to commit:\n. svn_commit'

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.stderr.write('Usage: %s source revision [destination]\n' % (
            sys.argv[0]))
        sys.exit(1)

    svn_merge(*sys.argv[1:])
