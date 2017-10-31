import itertools
import sys

class Node(object):
  def __init__(self, t, args):
      self.type = t
      self.args = tuple(args)
      
  def __repr__(self):
    return '(' + ' '.join(map(repr, (self.type, ) + self.args)) + ')'

  def __eq__(self, other):
    if not isinstance(other, self.__class__):
      return NotImplemented
    if self.type != other.type or len(self.args) != len(other.args):
      return False
    if hash(self) == hash(other):
      return True
    ret = reduce(lambda x,y: x and y, map(lambda x: x[0] == x[1],
                                          itertools.izip(self.args, other.args)))
    return ret
  
  def __ne__(self, other):
    if isinstance(other, self.__class__):
      return not self.__eq__(other)
    return NotImplemented

  def __hash__(self):
    h = hash((self.type, self.args)) & sys.maxsize
    assert h > 0
    return h
  
  def walk(self):
    ## NOTE: Various bits of code depend on this function doing
    ## post-order traversal.
    for child in self.args:
      if isinstance(child, Node):
        for c in child.walk():
          yield c
      else:
        yield child
    yield self

  def transform(self, f):
    # Pre-order traversal of the tree, i.e. call f() on node before
    # visiting children.o
    try:
      newnode = f(self)
    except StopIteration as e:
      # Skip processing this node's children
      return self
    if newnode is None or not isinstance(newnode, Node):
      return newnode
    newargs = tuple(child.transform(f) if isinstance(child, Node) else f(child)
                    for child in newnode.args)
    newnode.args = tuple(filter(lambda x: x is not None, newargs))
    return newnode
    
class Operator(object):
  operators = {}
  @classmethod
  def __getCache(cls, type):
    if type in Operator.operators:
      return Operator.operators[type]
    return None

  def __new__(cls, type, *args, **kwargs):
    """ Initilize the class and start processing """
    existing = cls.__getCache(type)
    if existing:
      return existing
    op = super(Operator, cls).__new__(cls)
    return op
  
  def __init__(self, type):
    if type in self.operators:
      return
    self.operators[type] = self
    self.type = type

  def __repr__(self):
    return "%s" % (self.type)

class Function(object):
  def __init__(self, type, args):
      self.type = type
      self.args = args

  def __repr__(self):
      #return "%s(%r)" % (self.__class__.__name__, self.type)
      return "%s(%s" % (self.type, ', '.join(self.args))

