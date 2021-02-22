#!/usr/bin/env python3

import argparse
from collections import defaultdict, namedtuple
import configparser
import datetime
from enum import Enum
import os
import shutil


ACTION_STATE_MARKER = '!'
class action_states(Enum):
  ACTIONABLE='^..^'
  WAIT='zzz'
  PRIORITY='!'


class todo(namedtuple('todo', 'text tags action_state is_completed number projects create_date')):
  @classmethod
  def fromline(cls, line):
    toks = line.rstrip().split()
    text = []
    tags = set()
    projects = set()
    action_state = action_states.ACTIONABLE
    done = False
    date = None
    for i, tok in enumerate(toks):
      if i == 0 and tok == 'X':
        done = True
      elif tok[0] == '#':
        tags.add(tok[1:])
      elif tok[0] == '@':
        projects.add(tok[1:])
      elif tok == ACTION_STATE_MARKER + action_states.WAIT.value:
        action_state = action_states.WAIT
      elif tok == ACTION_STATE_MARKER + action_states.PRIORITY.value:
        action_state = action_states.PRIORITY
      else:
        try:
          date = datetime.datetime.strptime(tok, '%Y-%m-%d').date()
        except ValueError:
          text.append(tok)

    return todo(text=' '.join(text), tags=tags, action_state=action_state, is_completed=done, number=-1, projects=projects, create_date=date)

  def rawstr(self, suppress_action_state=False):
    s = ('X ' if self.is_completed else '') + self.text + ' ' + ' '.join('#' + tag for tag in self.tags) + ' '.join('@' + project for project in self.projects) + (' ' + str(self.create_date) if self.create_date else '')
    if not suppress_action_state and self.action_state in (action_states.WAIT, action_states.PRIORITY):
      s += ' !' + self.action_state.value

    return s


def safeopen(flags):
  if not os.path.exists(filepath):
     return open(filepath, 'w')
  shutil.copyfile(filepath, filepath + '-bak')
  return open(filepath, flags)


def add(args):
  serialized = ' '.join(args.text) + ' ' + datetime.date.today().isoformat()
  safeopen('a+').write(serialized + '\n')


def add_silent(args):
  serialized = ' '.join(args.text + [ACTION_STATE_MARKER + action_states.WAIT.value, datetime.date.today().isoformat()])
  safeopen('a+').write(serialized + '\n')


def readtodos(filter_=None):
  if not filter_:
    filter_ = lambda x: x

  if not os.path.exists(filepath):
      return []

  return filter(filter_, (todo.fromline(line)._replace(number=i) for i, line in enumerate(open(filepath))))


def updatetodo(number, func):
  todos = list(readtodos())
  if number > len(todos):
    raise ValueError('no todo with id=%s' % number)
  for i, todo in enumerate(todos):
    if todo.number == number:
      break

  todo = func(todo)
  todos[i] = todo
  safeopen('w+').write('\n'.join(todo.rawstr() for todo in todos) + '\n')


def printtodos(filter_, show_action_state, suppress_number):
  todos = list(readtodos(filter_))
  if not todos:
      return
  digits = len(str(todos[-1].number))
  for todo in todos:
      n = str(todo.number).zfill(digits) if not suppress_number else '-'
      print(n, todo.rawstr(not show_action_state))


def lsa(args):
    args.all = True
    return ls(args)


def lp(args):
  def filter_(x):
    return len(x.projects) and not x.is_completed

  todos = list(readtodos(filter_))
  projects = defaultdict(list)
  for t in todos:
      for p in t.projects:
          projects[p].append(t)

  if not todos:
      return
  digits = len(str(todos[-1].number))
  for i, (p, tod) in enumerate(projects.items()):
      print('#', p)
      for todo in tod:
          n = str(todo.number).zfill(digits)
          print('-', n, todo.rawstr())
      if i < len(projects) - 1:
          print()

completed_filter = lambda x: not x.is_completed


def np(args):
  def filter_(todo):
      return not todo.projects

  printtodos(lambda x: completed_filter(x) and filter_(x), hasattr(args, 'all') and args.all, hasattr(args, 'export') and args.export)


def ls(args):
  projects = {}
  if hasattr(args, 'project'):
    projects = {project[1:] for project in args.project}

  def filterprojects(todo):
    if not projects:
      return True

    return set(todo.projects).intersection(projects)

  filter_ = lambda x: True

  if hasattr(args, 'waiting') and args.waiting:
    filter_ = lambda x: x.action_state == action_states.WAIT
  elif not hasattr(args, 'all') or not args.all:
    filter_ = lambda x: x.action_state == action_states.PRIORITY

  tags = set(getattr(args, 'tags', []))
  if tags:
      filter_ = lambda x: set(x.tags) & tags
  printtodos(lambda x: completed_filter(x) and filter_(x) and filterprojects(x), hasattr(args, 'all') and args.all, hasattr(args, 'export') and args.export)


def update_action_state(action_state):
    def inner(t):
        return t._replace(action_state=action_state)
    return inner


def mark_actionable(args):
  update_all(args.number, update_action_state(action_states.ACTIONABLE))


def mark_waiting(args):
  update_all(args.number, update_action_state(action_states.WAIT))


def mark_priority(args):
  update_all(args.number, update_action_state(action_states.PRIORITY))


def mark_done(args):
  def update(t):
    if t.is_completed:
        raise Exception('Already marked completed.')
    print('Marked completed: "%s"' % t.text)
    return t._replace(is_completed=True)

  return update_all(args.number, update)


def parse_numbers(numbers):
    num = []
    for n in numbers:
        if type(n) == int:
            num.append(n)
            continue
        n = n.split('-')
        assert len(n) <= 2
        if len(n) == 2:
            num += list(range(int(n[0]), int(n[1]) + 1))
        else:
            num.append(int(n[0]))

    return num

def update_all(numbers, fn):
  return [updatetodo(ni, fn) for ni in sorted(parse_numbers(numbers), reverse=True)]


def add_project(args):
  def update(t):
    projects = t.projects
    project = args.project
    if project[0] == '@':
      project = project[1:]
    projects.add(project)
    return t._replace(projects=projects)

  number = [arg for arg in args.number if arg[0] != '@']
  projects = [arg for arg in args.number if arg[0] == '@']
  args.number = number
  args.project = projects[0]
  return update_all(args.number, update)


def edit(args):
    os.system('%s %s' % (os.getenv('EDITOR'), filepath))


if __name__ == '__main__':
  import sys

  config = configparser.ConfigParser()
  try:
    config.read(os.path.expanduser('~/.todo-txt.cfg'))
    filepath = os.path.expanduser(config.get('default', 'filepath'))
  except configparser.NoSectionError:
    filepath = 'todo.txt'

  parser = argparse.ArgumentParser(description='todo.txt')
  subparsers = parser.add_subparsers(title='commands')
  sub_parser = subparsers.add_parser('add', aliases=['a'])
  sub_parser.add_argument('text', nargs='+')
  sub_parser.set_defaults(func=add)

  sub_parser = subparsers.add_parser('add-silent', aliases=['as'])
  sub_parser.add_argument('text', nargs='+')
  sub_parser.set_defaults(func=add_silent)

  sub_parser = subparsers.add_parser('list', aliases=['ls'])
  sub_parser.add_argument('--all', action='store_true')
  sub_parser.add_argument('--waiting', action='store_true')
  sub_parser.add_argument('--export', action='store_true')
  sub_parser.add_argument('project', nargs='*')
  sub_parser.set_defaults(func=ls)

  sub_parser = subparsers.add_parser('list-all', aliases=['lsa'])
  sub_parser.add_argument('tags', nargs='*')
  sub_parser.set_defaults(func=lsa)

  sub_parser = subparsers.add_parser('list-projects', aliases=['lp'])
  sub_parser.set_defaults(func=lp)

  sub_parser = subparsers.add_parser('no-projects', aliases=['np'])
  sub_parser.set_defaults(func=np)

  sub_parser = subparsers.add_parser('mark-priority', aliases=['mp'])
  sub_parser.add_argument('number', nargs='+', type=str)  # TODO
  sub_parser.set_defaults(func=mark_priority)

  sub_parser = subparsers.add_parser('mark-actionable', aliases=['ma'])
  sub_parser.add_argument('number', nargs='+', type=str)  # TODO
  sub_parser.set_defaults(func=mark_actionable)

  sub_parser = subparsers.add_parser('mark-waiting', aliases=['mw'])
  sub_parser.add_argument('number', nargs='+', type=str)  # TODO
  sub_parser.set_defaults(func=mark_waiting)

  sub_parser = subparsers.add_parser('do', aliases=['x'])
  sub_parser.add_argument('number', nargs='+', type=str)  # TODO
  sub_parser.set_defaults(func=mark_done)

  sub_parser = subparsers.add_parser('proj', aliases=['p'])
  sub_parser.add_argument('number', nargs='+', type=str)  # TODO
  sub_parser.set_defaults(func=add_project)

  sub_parser = subparsers.add_parser('edit', aliases=['e'])
  sub_parser.set_defaults(func=edit)

  args = parser.parse_args()

  if hasattr(args, 'func'):
    try:
      args.func(args)
    except Exception as e:
      print(e)
      sys.exit(1)
  else:
    ls(namedtuple('args', 'a w')(None, None))
