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

1. Remove the branch:
   $ svn rm https://svnserver/branches/branch
   $ svn commit
     ...
   Committed revision 1234

2. Copy the current trunk into a new branch:
   $ svn cp https://svnserver/branches/trunk https://svnserver/branches/branch
   $ svn commit
   $ svn co https://svnserver/branches/branch
   $ cd branch

3. Start rebasing: (Use the branch before we rename it)
   $ ./svn_rebase.py https://svnserver/branches/branch@1233

4. Resolve conflicts if there are any:
   It'll show a message like: Use "svn commit -F r123_commit_message" to commit
   - Manually edit files to resolve conficts
   - $ svn resolve file1
   - $ svn commit -F r123_commit_message

5. Continue the merge:
   $ ./svn_rebase.py --continue

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
   $ ./svn_rebase.py -r1000-1005,1008 https://svnserver/branches/branch

   Or if your target directory is different from your source directory:
   $ ./svn_rebase.py -r 1000-1005,1008 -d dir2 https://svnserver/branches/branch/dir
'''

import cPickle
import os
import optparse
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

def main(sysargs):
    """Handles the svn rebase command line usage

    Arguments:

    sysargs - the args string, usually sys.argv[1:]

    """
    parser = optparse.OptionParser(
            usage=('%prog [options] source_url\n\n'
                '   or: %prog --continue | --abort'))
#    parser.add_option('-i', '--interactive',
#            help=('Make a list of commits which are about to be rebased.  Let'
#                ' the user edit that list before rebasing.'),
#            action='store_true', dest='interactive', default=False)
    parser.add_option('-a', '--abort',
            help='Remove the state of the rebasing process.',
            action='store_true', dest='abort')
    parser.add_option('-c', '--continue',
            help=('Restart the rebasing process after having resolved a merge'
                ' conflict.'), action='store_true', dest='cont',
            default=False)
#    parser.add_option('-m', '--manual-commit',
#            help='After merging a commit, let the user commit manually.',
#            action='store_false', dest='auto_commit', default=True)
    parser.add_option('-r', '--revisions',
            help='Revisions to merge', action='store', dest='revisions')
    parser.add_option('-d', '--destination',
            help='Target directory of the merges.', action='store',
            dest='destination')

    options, args = parser.parse_args(sysargs)
    state = {}
    if options.cont:
        state = load_state()
        if not state:
            sys.stderr.write('No rebase in progress?\n')
            sys.exit(1)
        if options.revisions or options.abort or options.destination or args:
            parser.error('option -c / --continue can only be used '
                    'without other options.')

    elif options.abort:
        if options.cont or options.revisions or options.destination or args:
            parser.error('option -a / --abort can only be used '
                    'without other options.')
        remove_state_file()
        sys.exit(0)

    else:
        if len(args) != 1:
            sys.stderr.write('Please specify the source url.\n')
            sys.exit(1)
        state['source'] = args[0]
        state['revisions'] = options.revisions
        state['destination'] = options.destination

    try:
        svn_rebase(**state)
    except LocalModificationsException:
        save_state(*state)
        sys.stderr.write('Please commit all local modifications before '
                'merging.\n')
        sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[1:])
