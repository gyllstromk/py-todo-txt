#!/usr/bin/env python3

import argparse
from collections import namedtuple
import configparser
from enum import Enum
import os


class action_states(Enum):
  ACTIONABLE='^..^'
  WAIT='Zzz'


class todo(namedtuple('todo', 'text tags action_state')):
  @classmethod
  def fromline(cls, line):
    toks = line.rstrip().split()
    text = []
    tags = []
    action_state = action_states.ACTIONABLE
    for tok in toks:
      if tok[0] == '#':
        tags.append(tok[1:])
      elif tok == '!' + action_states.WAIT.value:
        action_state = action_states.WAIT
      else:
        text.append(tok)

    return todo(text=' '.join(text), tags=tags, action_state=action_state)

  def rawstr(self):
    return self.text + ' ' + ' '.join('#' + tag for tag in self.tags)


def add(args):
  open(filepath, 'a+').write(' '.join(args.text) + '\n')


def readtodos(filter_=None):
  if not filter_:
    filter_ = lambda x: x

  return filter(filter_, (todo.fromline(line) for line in open(filepath, 'w+')))


def printtodos(filter_=None):
  for i, todo in enumerate(readtodos(filter_)):
    print(i, todo.rawstr())


def ls(args):
  printtodos()


def awaiting(args):
  printtodos(lambda x: x.action_state == action_states.WAIT)


def actionable(args):
  printtodos(lambda x: x.action_state == action_states.ACTIONABLE)


if __name__ == '__main__':
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
  sub_parser.set_defaults(func=ls)

  sub_parser = subparsers.add_parser('awaiting', aliases=['aw'])
  sub_parser.set_defaults(func=awaiting)

  sub_parser = subparsers.add_parser('actionable', aliases=['ac'])
  sub_parser.set_defaults(func=actionable)

  args = parser.parse_args()
  args.func(args)
