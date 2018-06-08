#!/usr/bin/env python3

import argparse
from collections import namedtuple
import configparser
from enum import Enum
import os
import shutil


class action_states(Enum):
  ACTIONABLE='^..^'
  WAIT='Zzz'


class todo(namedtuple('todo', 'text tags action_state is_completed number projects')):
  @classmethod
  def fromline(cls, line):
    toks = line.rstrip().split()
    text = []
    tags = set()
    projects = set()
    action_state = action_states.ACTIONABLE
    done = False
    for i, tok in enumerate(toks):
      if i == 0 and tok == 'X':
        done = True
      elif tok[0] == '#':
        tags.add(tok[1:])
      elif tok[0] == '@':
        projects.add(tok[1:])
      elif tok == '!' + action_states.WAIT.value:
        action_state = action_states.WAIT
      else:
        text.append(tok)

    return todo(text=' '.join(text), tags=tags, action_state=action_state, is_completed=done, number=-1, projects=projects)

  def rawstr(self):
    s = ('X ' if self.is_completed else '') + self.text + ' ' + ' '.join('#' + tag for tag in self.tags) + ' '.join('@' + project for project in self.projects)
    if self.action_state == action_states.WAIT:
      s += ' !' + self.action_state.value

    return s


def safeopen(flags):
  shutil.copyfile(filepath, filepath + '-bak')
  return open(filepath, flags)


def add(args):
  safeopen('a+').write(' '.join(args.text) + '\n')


def readtodos(filter_=None):
  if not filter_:
    filter_ = lambda x: x

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


def printtodos(filter_=None):
  todos = list(readtodos(filter_))
  digits = len(str(todos[-1].number))
  for todo in todos:
    print(str(todo.number).zfill(digits), todo.rawstr())


def ls(args):
  projects = {}
  if hasattr(args, 'project'):
    projects = {project[1:] for project in args.project}

  def filterprojects(todo):
    if not projects:
      return True

    return set(todo.projects).intersection(projects)

  filter_ = lambda x: True
  completed_filter = lambda x: not x.is_completed

  if hasattr(args, 'waiting') and args.waiting:
    filter_ = lambda x: x.action_state == action_states.WAIT
  elif not hasattr(args, 'all'):
    filter_ = lambda x: x.action_state == action_states.ACTIONABLE
  printtodos(lambda x: completed_filter(x) and filter_(x) and filterprojects(x))


def mark_actionable(args):
  def update(t):
    return t._replace(action_state=action_states.ACTIONABLE)

  updatetodo(args.number[0], update)


def mark_waiting(args):
  def update(t):
    return t._replace(action_state=action_states.WAIT)

  updatetodo(args.number[0], update)


def mark_done(args):
  def update(t):
    if t.is_completed:
        raise Exception('Already marked completed.')
    return t._replace(is_completed=True)

  updatetodo(args.number[0], update)


def add_project(args):
  def update(t):
    projects = t.projects
    project = args.project
    if project[0] == '@':
      project = project[1:]
    projects.add(project)
    return t._replace(projects=projects)

  updatetodo(args.number[0], update)


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

  sub_parser = subparsers.add_parser('list', aliases=['ls'])
  sub_parser.add_argument('--all', action='store_true')
  sub_parser.add_argument('--waiting', action='store_true')
  sub_parser.add_argument('project', nargs='*')
  sub_parser.set_defaults(func=ls)

  sub_parser = subparsers.add_parser('mark-actionable', aliases=['ma'])
  sub_parser.add_argument('number', nargs='+', type=int)  # TODO
  sub_parser.set_defaults(func=mark_actionable)

  sub_parser = subparsers.add_parser('mark-waiting', aliases=['mw'])
  sub_parser.add_argument('number', nargs='+', type=int)  # TODO
  sub_parser.set_defaults(func=mark_waiting)

  sub_parser = subparsers.add_parser('do', aliases=['x'])
  sub_parser.add_argument('number', nargs='+', type=int)  # TODO
  sub_parser.set_defaults(func=mark_done)

  sub_parser = subparsers.add_parser('proj')
  sub_parser.add_argument('number', nargs='+', type=int)  # TODO
  sub_parser.add_argument('project')  # TODO
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
