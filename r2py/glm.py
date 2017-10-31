
import collections
import functools
import re
import rpy2.robjects as robjects
import rpy2.rinterface as rinterface

from . import reval
from . import ri2pi
from . import rparser
from .tree import Node, Operator

class GLM():
  def __init__(self, obj=None):
    self.__rclass = tuple(obj.rclass)[0]
    self.dict = {}
    self._equation = None
    self._stab = None
    self._link = None
    self.obj = obj
    if obj:
      for name in obj.names:
        setattr(self, name.replace('.', '_'),
                functools.partial(self.lm_getattr, name))
      self.dict = dict((n[0], type(n[1])) for i, n in enumerate(obj.items()))
    
  def lm_getattr(self, name):
    return ri2pi(self.obj.rx2(name))

  def attrs(self):
    return self.dict.keys()
    return [k.replace('.', '_') for k in self.dict.keys()]

  def attr(self, a):
    return self.obj.rx2(a)

  @property
  def link(self):
    if not self._link:
      self._link = tuple(self.obj.rx2('family').rx2('link'))[0]
    return self._link

  def _polys(self):
    raw_model = self.obj.rx2('model')
    for node in self.equation.walk():
      if (not isinstance(node, Node) or node.type != Operator('poly') or
          len(node.args) == 4):
        continue
      name = '%s(%s, %d)' % (node.type, reval.to_rexpr(node.args[0]),
                             node.args[1])
      coefs = robjects.r.attr(raw_model.rx2(name), which="coefs")
      assert coefs != rinterface.NULL
      norm2 = coefs.rx2('norm2')[1:]
      alpha = coefs.rx2('alpha')
      node.args = node.args + (Node(Operator('list'), norm2),
                               Node(Operator('list'), alpha))

  def _cse(self):
    cache = dict()
    reps = dict()
    visited = dict()
    def match(n):
      if not isinstance(n, Node):
        return n
      if hash(n) in visited:
        # NOTE: special case since transform is pre-order, i.e. we just
        # created a var node and now get called with the child of a var
        # node we just created.
        return n
      ms = filter(lambda x: x == n, cache.values())
      if ms:
        assert len(ms) == 1, 'matched too many nodes'
        m = ms[0]
        if hash(m) not in reps:
          reps[hash(m)] = Node(Operator('var'), (hash(m), m))
          visited[hash(m)] = 1
        assert m == n, 'not equal %s != %s' % (repr(n), repr(m))
        assert hash(n) != hash(m), 'matched node to itself'
        return reps[hash(m)]
      if n.type == Operator('poly') or n.type == Operator('=='):
        cache[hash(n)] = n
        reps[hash(n)] = Node(Operator('var'), (hash(n), n))
        visited[hash(n)] = 1
        return reps[hash(n)]
      return n
    self._equation = self.equation.transform(match)

  def to_py(self, fname):
    return reval.to_py(self.equation, fname)

  def to_pyx(self, fname):
    return reval.to_pyx(self.equation, fname)

  def to_numba(self, fname):
    return reval.to_numba(self.equation, fname, self.output)

  def eval(self, df):
    return reval.evalr(self.equation, df)
  
  @property
  def equation(self):
    '''Return a tree that represents the model equation.'''
    if not self._equation:
      coefs = self.coefficients().dropna()
      prods = [Node(Operator('*'), [rparser.parse(x[0]), x[1]])
               for x in coefs.itertuples()]
      if self.link == 'logit':
        inv_link = Operator('inv_logit')
      else:
        raise RuntimeError('unknown link function %s' % self.link)
      expr = Node(Operator('+'), prods)
      root = Node(inv_link, [Node(Operator('var'),
                                            (hash(expr), expr))])
      self._equation = reval.make_inputs(root)
      self._cse()
      self._polys()
    return self._equation

  @property
  def stab(self):
    return dict((n, 1) for n in self.syms)

  @property
  def syms(self):
    return reval.find_inputs(self.equation)

  def frame(self):
    return self.data()
  
  @property
  def hstab(self):
    frame = self.frame()
    categoricals = filter(lambda c: frame[c].dtype, frame)
    regexp = re.compile('((' + '|'.join(categoricals) + ')(.*))')
    res = {}
    for k, v in self.stab.items():
      m = regexp.match(k)
      if m:
        cat = m.group(2)
        level = m.group(3)
        if cat in res:
          assert level not in res[cat]
          res[cat][level] = 1
        else:
          res[cat] = {level: 1}
      else:
        res[k] = v
    return res

  @property
  def output(self):
    '''Return the response variables in the model equation.'''
    fm = self.formula()
    formula = re.sub('\s+', ' ', fm.r_repr())
    lhs, _ = formula.split('~')
    return lhs.strip()
