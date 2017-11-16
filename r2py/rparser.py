from pyparsing import *
import re
ParserElement.enablePackrat()

from .tree import Node, Operator

import pdb

def rparser():
  expr = Forward()

  lparen = Literal("(").suppress()
  rparen = Literal(")").suppress()
  double = Word(nums + ".").setParseAction(lambda t:float(t[0]))
  integer = pyparsing_common.signed_integer
  number = pyparsing_common.number
  ident = Word(initChars = alphas + "_", bodyChars = alphanums + "_" + ".")
  string = dblQuotedString
  funccall = Group(ident + lparen + Group(Optional(delimitedList(expr))) +
                   rparen + Optional(integer)).setResultsName("funccall")

  operand = number | string | funccall | ident

  expop = Literal('^')
  multop = oneOf('* /')
  plusop = oneOf('+ -')
  introp = oneOf('| :')

  expr << infixNotation(operand,
                        [(expop, 2, opAssoc.RIGHT),
                         (introp, 2, opAssoc.LEFT),
                         (multop, 2, opAssoc.LEFT),
                         (plusop, 2, opAssoc.LEFT),]).setResultsName('expr')
  return expr

PARSER = rparser()

def parse(text):
  def walk(l):
    ## ['log', [['cropland', '+', 1]]]
    ## ['poly', [['log', [['cropland', '+', 1]]], 3], 3]
    ## [[['factor', ['unSub'], 21], ':', ['poly', [['log', [['cropland', '+', 1]]], 3], 3], ':', ['poly', [['log', [['hpd', '+', 1]]], 3], 2]]]
    if type(l) in (int, float):
        return l
    if isinstance(l, str):
      if l == 'Intercept' or l == '"Intercept"':
        return 1
      elif l[0] == '"' and l[-1] == '"':
        return l[1:-1]
      else:
        return l
    if len(l) == 1 and type(l[0]) in (int, str, float, ParseResults):
      return walk(l[0])
    if l[0] == 'factor':
      assert len(l) == 3, "unexpected number of arguments to factor"
      assert len(l[1]) == 1, "argument to factor is an expression"
      assert type(l[2]) == int, "second argument to factor is not an int"
      return Node(Operator('=='), (Node(Operator('in'),
                                        (l[1][0], 'float32[:]')), l[2]))
    if l[0] == 'poly':
      assert len(l) in (2, 3), "unexpected number of arguments to poly"
      assert isinstance(l[1][1], int), "degree argument to poly is not an int"
      inner = walk(l[1][0])
      degree = l[1][1]
      if len(l) == 2:
        pwr = 1
      else:
        assert type(l[2]) == int, "power argument to poly is not an int"
        pwr = l[2]
      return Node(Operator('sel'), (Node(Operator('poly'), (inner, degree)),
                                    pwr))
    if l[0] == 'log':
      assert len(l) == 2, "unexpected number of arguments to log"
      args = walk(l[1])
      return Node(Operator('log'), [args])
    if l[0] == 'scale':
      assert len(l[1]) in (3, 5), "unexpected number of arguments to scale"
      args = walk(l[1][0])
      return Node(Operator('scale'), [args] + l[1][1:])
    if l[0] == 'I':
      assert len(l) == 2, "unexpected number of arguments to I"
      args = walk(l[1])
      return Node(Operator('I'), [args])
    # Only used for testing
    if l[0] in ('sin', 'tan'):
      assert len(l) == 2, "unexpected number of arguments to %s" % l[0]
      args = walk(l[1])
      return Node(Operator(l[0]), [args])
    if l[0] in ('max', 'min'):
      assert len(l) == 2, "unexpected number of arguments to %s" % l[0]
      assert len(l[1]) == 2, "unexpected number of arguments to %s" % l[0]
      left = walk(l[1][0])
      right = walk(l[1][1])
      return Node(Operator(l[0]), (left, right))
    if l[0] == 'exp':
      assert len(l) == 2, "unexpected number of arguments to exp"
      args = walk(l[1])
      return Node(Operator('exp'), [args])
    if l[0] == 'inv_logit':
      assert len(l) == 2, "unexpected number of arguments to inv_logit"
      args = walk(l[1])
      return Node(Operator('inv_logit'), [args])
      

    ## Only binary operators left
    if len(l) == 1:
      pdb.set_trace()
      pass
    assert len(l) % 2 == 1, "unexpected number of arguments for binary operator"
    assert len(l) != 1, "unexpected number of arguments for binary operator"
    ## FIXME: this only works for associative operators.  Need to either
    ## special-case division or include an attribute that specifies
    ## whether the op is associative.
    left = walk(l.pop(0))
    op = l.pop(0)
    right = walk(l)
    if type(right) != Node:
      return Node(Operator(op), (left, right))
    elif right.type.type == op:
      return Node(Operator(op), (left, ) + right.args)
    return Node(Operator(op), (left, right))

  ### FIXME: hack
  new_text = re.sub('newrange = c\((\d), (\d+)\)', '\\1, \\2', text)
  new_text = new_text.replace('rescale(', 'scale(')
  nodes = PARSER.parseString(new_text, parseAll=True)
  tree =  walk(nodes)
  if isinstance(tree, (str, int, float)):
    tree = Node(Operator('I'), [tree])
  return tree
