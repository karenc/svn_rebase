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

manual_commit_message = ('Use "svn commit -F commit_message" to commit '
        'after the conflicts are resolved')

class CallError(Exception):
    pass

class SvnConflictException(Exception):
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
    filename = 'commit_message'
    author, message = get_log_message(revision, source)
    message = message.strip()
    f = open(filename, 'w')
    f.write(message.encode('utf-8'))
    if not re.search('\(([^ ]* )?merge r[^)]*\)$', message):
        f.write(' (%s, merge r%s)' % (author, revision))
    f.close()
    if auto_commit:
        try:
            call(['svn', 'commit', '-F', filename])
        except CallError:
            print manual_commit_message
            raise SvnConflictException
    else:
        print manual_commit_message
    return message

if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.stderr.write('Usage: %s source revision [destination]\n' % (
            sys.argv[0]))
        sys.exit(1)

    try:
        svn_merge(*sys.argv[1:])
    except SvnConflictException:
        # we don't care about the exception, we've already printed out the
        # message, this exception is for using svn_merge as a library
        pass
