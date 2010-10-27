#!/usr/bin/env python

'''
This script automatically rebases a svn repository.

See README for details.
'''

import cPickle
import os
import optparse
import subprocess
import sys
import re
from xml.etree import ElementTree


STATE_FILENAME = 'svn_rebase.state'
INTERACTIVE_FILENAME = 'svn_rebase.todo'

manual_commit_message = ('Use "svn commit -F commit_message" to commit '
        'after the conflicts are resolved')


INTERACTIVE_COMMANDS = {
        'p': '(pick) use commit',
        'e': '(edit) use commit, but stop for amending',
        's': '(squash) use commit, but meld into previous commit',
        }


class InvalidInteractiveFile(Exception):
    pass


class LocalModificationsException(Exception):
    pass


class SvnConflictException(Exception):
    pass


class CallError(Exception):
    pass


def call(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise CallError
    return stdout

def save_state(source, **kwargs):
    f = open(STATE_FILENAME, 'w')
    state = {
            'source': source,
            }
    state.update(kwargs)
    cPickle.dump(state, f)
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

def get_log_message(revision, source):
    results = call(['svn', 'log', '--xml', '-r', revision, source])
    root = ElementTree.fromstring(results)
    return root.findtext('logentry/author'), root.findtext('logentry/msg')

def svn_merge(source, revisions, destination=None, auto_commit=False):
    for revision in revisions:
        call_args = ['svn', 'merge', '--accept', 'postpone', '-c',
                str(revision), source]
        if destination is not None:
            call_args.append(destination)
        call(call_args)
    filename = 'commit_message'
    author, message = get_log_message(str(revision), source)
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

def _get_source_revisions(source, stop_on_copy):
    command = ['svn', 'log', '--xml']
    if stop_on_copy:
        command.append('--stop-on-copy')
    command.append(source)
    return call(command)

def get_source_revisions(source, stop_on_copy=False):
    out = _get_source_revisions(source, stop_on_copy=stop_on_copy)
    root = ElementTree.fromstring(out)
    rev = []
    for entry in root.findall('logentry'):
        rev.append({
            'revision': int(entry.get('revision')),
            'msg': entry.findtext('msg'),
            })
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

def write_interactive(revisions):
    """Writes out the file for the interactive option.

    :Parameters:
      - `revisions`: a list, [{'revision': 1234, 'msg': 'xxxx'}, ..]
    """
    output = []
    for r in revisions:
        # get the first non empty line of the commit message
        msg = [line for line in r['msg'].splitlines() if line.strip()]
        msg = msg[0] if msg else ''
        output.append(' '.join(['pick', str(r['revision']), msg[:80]]))
        output.append('\n')
    output.append('''
# Commands:
%(commands)s
#
#
''' % {
    'commands': '\n'.join(['#   %s = %s' % (command, desc)
        for command, desc in INTERACTIVE_COMMANDS.items()]),
    })
    f = open(INTERACTIVE_FILENAME, 'w')
    f.write(''.join(output))
    f.close()
    subprocess.call(['editor', INTERACTIVE_FILENAME])

def read_interactive(allowed_revisions):
    """Read from the interactive file, check the output with the allowed
    revisions.

    :Parameters:
      - `allowed_revisions`: a list of allowed revisions
    :Returns: a list of revisions, and a dict of {revision: 'command'}, ...}
    """
    revisions = []
    interactive_options = {}
    f = open(INTERACTIVE_FILENAME)
    for line in f.readlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) < 2:
            raise InvalidInteractiveFile('A line must at least have a '
                    'command and a revision.')
        command = parts[0]
        if command[0] not in INTERACTIVE_COMMANDS:
            raise InvalidInteractiveFile('Command "%s" is not found.' % (
                command))
        if not revisions and command == 's':
            raise InvalidInteractiveFile('squash cannot be used as the'
                    ' command of the first commit.')
        try:
            revision = int(parts[1])
        except:
            raise InvalidInteractiveFile('Revision must be a number.')
        if revision not in allowed_revisions:
            print 'allowed revisions', allowed_revisions
            raise InvalidInteractiveFile('Revision "%s" cannot be found in '
                    'branch.' % revision)
        if command == 's':
            revisions[-1].append(revision)
        else:
            interactive_options[revision] = command
            revisions.append([revision])
    f.close()
    os.remove(INTERACTIVE_FILENAME)
    return revisions, interactive_options

def svn_rebase(source, revisions=None, destination=None, auto_commit=True,
        interactive=False):
    if call(['svn', 'diff']):
        raise LocalModificationsException
    if revisions is None:
        revision_log = get_source_revisions(source, stop_on_copy=True)
    else:
        if isinstance(revisions, str):
            revisions = parse_revisions(revisions)
        revision_log = [r for r in get_source_revisions(source)
                if r['revision'] in revisions]

    revision_log.sort(lambda a, b: cmp(a['revision'], b['revision']))
    revisions = [r['revision'] for r in revision_log]
    interactive_options = {}

    if interactive:
        write_interactive(revision_log)
        revisions, interactive_options = read_interactive(revisions)
    else:
        revisions = [[r] for r in revisions]

    # revisions in groups
    # e.g. [[1000], [1001, 1002]]
    while revisions:
        r = revisions.pop(0)
        save_state(source, revisions=revisions, destination=destination,
                auto_commit=auto_commit, interactive=interactive)
        conflict = False
        try:
            message = svn_merge(source, r, destination,
                    auto_commit=auto_commit)
            print 'Merged %s (%s)' % (r, message)
        except SvnConflictException:
            conflict = True
        if not auto_commit or conflict:
            print '"%s --continue" to continue the merge' % sys.argv[0]
            sys.exit(1)
    remove_state_file()

def main():
    """Handles the svn rebase command line usage
    """

    sysargs = sys.argv[1:]

    parser = optparse.OptionParser(
            usage=('%prog [options] source_url\n\n'
                '   or: %prog --continue | --abort'))
    parser.add_option('-i', '--interactive',
            help=('Make a list of commits which are about to be rebased.  Let'
                ' the user edit that list before rebasing.'),
            action='store_true', dest='interactive', default=False)
    parser.add_option('-a', '--abort',
            help='Remove the state of the rebasing process.',
            action='store_true', dest='abort')
    parser.add_option('-c', '--continue',
            help=('Restart the rebasing process after having resolved a merge'
                ' conflict.'), action='store_true', dest='cont',
            default=False)
    parser.add_option('-m', '--manual-commit',
            help='After merging a commit, let the user commit manually.',
            action='store_false', dest='auto_commit', default=True)
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
            sys.stderr.write('Please specify the source url.\n\n')
            parser.print_help()
            sys.exit(1)
        state['source'] = args[0]
        state['revisions'] = options.revisions
        state['destination'] = options.destination
        state['auto_commit'] = options.auto_commit
        state['interactive'] = options.interactive

    try:
        svn_rebase(**state)
    except LocalModificationsException:
        save_state(**state)
        sys.stderr.write('Please commit all local modifications before '
                'merging.\n')
        sys.exit(1)

