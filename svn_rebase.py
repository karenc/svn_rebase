#!/usr/bin/env python

'''This script does merging using svn_merge.py with multiple
revisions.  For example:

./svn_rebase.py 1000-1005,1008 http://svnserver/path

will merge revisions 1000-1005 and 1008 from
http://svnserver/path into the current directory.

It merges one revision at a time.  If there's a conflict, the user can resolve
it manually and continue the merge.


Reasons for using this script:

    svnmerge also allows merging multiple commits.  svnmerge will
merge all the commits into the current tree and let the user commits
it.  The problem comes when the user merges lots of commits in one
go, losing version history and making "svn ann" useless.

    This script will commit after merging every commit, and commit with the
original message with the original revision number.  So it is possible to use
"svn ann" to find out which commit changed what line and the commit message
with it.

-----

Scenario 1: Rebase

You created a branch from trunk, trunk has since changed.  You want
to update your branch with trunk changes.

1. Rename the branch:
   $ svn mv branch branch_old
   $ svn commit
     ...
   Committed revision 1234

2. Copy the current trunk into a new branch:
   $ svn cp trunk branch
   $ svn commit
   $ cd branch

3. Start rebasing: (Use the branch before we rename it)
   $ ./svn_rebase.py https://svnserver/branches/branch@1233

4. Resolve conflicts if there are any:
   It'll show a message like: Use "svn commit -F r123_commit_message" to commit
   - Manually edit files to resolve conficts
   - $ svn resolve file1
   - $ svn commit -F r123_commit_message

5. Continue the merge:
   $ ./svn_rebase.py

6. (Optional) Remove the old branch and rename the new one.

-----

Scenario 2: Merging from one tree to another tree

You want to merge changes from one branch into another branch.  For
example, you created a branch from trunk to fix a ticket, now it's
done and you want to merge it back into trunk.

1. Go to the trunk directory

2. Start merging:
   $ ./svn_rebase.py https://svnserver/branches/trunk_1234

3. Resolve conflicts and continue the merge (See steps 4 and 5 in
   scenario 1)

-----

Scenario 3: Merging some changesets from one tree to another tree

You want to cherry pick changesets to merge from one tree to another.
For example, you want to get some changesets from "branch" to
"trunk".

1. Go to the trunk directory

2. Select changesets to merge:
   $ ./svn_rebase.py https://svnserver/branches/branch 1000-1005,1008

   Or if your target directory is different from your source directory:
   $ ./svn_rebase.py https://svnserver/branches/branch/dir 1000-1005,1008 dir2
'''

import cPickle
import os
import subprocess
import sys

from lxml import etree

sys.path.append(os.path.dirname(__file__))
import svn_merge

STATE_FILENAME = 'svn_rebase.state'

class LocalModificationsException(Exception):
    pass

class CallError(Exception):
    pass

def call(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise CallError
    return stdout

def save_state(source, revisions=None, destination=None):
    f = open(STATE_FILENAME, 'w')
    cPickle.dump({
        'source': source,
        'revisions': revisions,
        'destination': destination,
        }, f)
    f.close()

def load_state():
    try:
        f = open(STATE_FILENAME)
        state = cPickle.load(f)
        f.close()
        os.remove(STATE_FILENAME)
        return state
    except IOError:
        pass

remove_state_file = load_state

def _get_source_revisions(source, stop_on_copy):
    command = ['svn', 'log', '--xml']
    if stop_on_copy:
        command.append('--stop-on-copy')
    command.append(source)
    return call(command)

def get_source_revisions(source, stop_on_copy=False):
    out = _get_source_revisions(source, stop_on_copy=stop_on_copy)
    root = etree.fromstring(out)
    rev = []
    for entry in root.xpath('/log/logentry'):
        rev.append(int(entry.get('revision')))
    if stop_on_copy:
        # the first rev is the copy commit
        rev.pop()
    return rev

def parse_revisions(revisions):
    '''
    :Parameters:
      - `revisions`: str, e.g. '1000-1005,1008'
    :Returns: a list of revisions, e.g. [1000, 1001, 1002,
      1003, 1004, 1005, 1008]
    '''
    revisions = revisions.split(',')
    expanded = []
    for r in revisions:
        if '-' in r:
            start = int(r.split('-')[0])
            end = int(r.split('-')[1])
            expanded.extend(range(start, end + 1))
        else:
            expanded.append(int(r))
    return expanded

def svn_rebase(source, revisions=None, destination=None):
    if call(['svn', 'diff']):
        raise LocalModificationsException
    if revisions is None:
        revisions = get_source_revisions(source, stop_on_copy=True)
    else:
        if isinstance(revisions, str):
            revisions = parse_revisions(revisions)
        source_revisions = get_source_revisions(source)
        revisions = list(set(source_revisions).intersection(set(revisions)))

    revisions.sort()

    while revisions:
        r = revisions.pop(0)
        save_state(source, revisions, destination)
        try:
            message = svn_merge.svn_merge(source, str(r), destination, auto_commit=True)
            print 'Merged %s (%s)' % (r, message)
        except svn_merge.CallError:
            print ('Use "svn commit -F r%s_commit_message" to commit '
                    'after the conflicts are resolved' % r)
            print '"%s" to continue the merge' % sys.argv[0]
            sys.exit(1)
    remove_state_file()

if __name__ == '__main__':
    state = load_state()
    if len(sys.argv) < 2 and state is None:
        sys.stderr.write('Usage: %s source [revisions] [destination]\n' % (
            sys.argv[0]))
        sys.exit(1)

    if sys.argv[1:]:
        args = sys.argv[1:]
    else:
        args = [state['source'], state['revisions'], state['destination']]

    try:
        svn_rebase(*args)
    except LocalModificationsException:
        save_state(*args)
        sys.stderr.write('Please commit all local modifications before '
                'merging.\n')
        sys.exit(1)
