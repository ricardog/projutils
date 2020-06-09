
import collections
import re

import rpy2.robjects as robjects
import rpy2.rinterface as rinterface
import rpy2.robjects.packages

robjects.packages.importr('Matrix')
robjects.packages.importr('lme4')

from . import reval
from .ri2pi import ri2pi
from . import rparser
from .tree import Node, Operator

class MerMod(robjects.methods.RS4):
  '''Generic class for representing mixed-effect models.  This class is
meant to be used as a mixin in a model-specific class, c.f. lmermod.py
or glmermod.py, both of which inherit from this class.  In theory it
should be possible to create new classes for new model-types in lme4
(and perhaps other packages as well) but I have not tried it.
  '''
  def __init__(self, obj=None):
    self.pkg = robjects.packages.importr(self.__class__.__rpackagename__)
    self.__rclass = tuple(obj.rclass)[0]
    self._equation = None
    self._stab = None
    super(MerMod, self).__init__(obj)

  def call_method(self, what):
    method = getattr(self.pkg, what + '_' + self.__class__.__rname__)
    return method(self)

  def fixef(self):
    '''Return a DataFrame with the model's fixed-effect coefficients.'''
    return ri2pi(self.call_method('fixef'))

  def terms(self):
    '''Return a list of predictor variables in the model equation.'''
    fm = self.call_method('terms')
    formula = re.sub('\s+', ' ', fm.r_repr())
    lhs, rhs = formula.split('~')
    lhs = lhs
    prods = [x.strip() for x in rhs.split('+')]
    return prods

  def frame(self):
    '''Raturn the data frame used to fit the model.'''
    return ri2pi(self.slots['frame'])

  def _polys(self):
    ## Need to get raw frame, i.e. not translated by ri2pi, so that we
    ## can get the coefficients for each poly().
    raw_frame = self.slots['frame']
    def find_norm2_alpha(node):
      if (not isinstance(node, Node) or node.type != Operator('poly') or
          len(node.args) == 4):
        return node
      name = '%s(%s, %d)' % (node.type, reval.to_rexpr(node.args[0]),
                             node.args[1])
      coefs = robjects.r.attr(raw_frame.rx2(name), which="coefs")
      assert coefs != rinterface.NULL
      norm2 = coefs.rx2('norm2')[1:]
      alpha = coefs.rx2('alpha')
      return Node(Operator('poly'), node.args +
                  (Node(Operator('list'), norm2),
                   Node(Operator('list'), alpha)))
    self.equation.transform(find_norm2_alpha)

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
      ms = tuple(filter(lambda x: x == n, cache.values()))
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
    oseries = self.frame()[self.output]
    orange = (oseries.min(), oseries.max())
    return reval.to_numba(self.equation, fname, self.output, orange=orange)
  
  def eval(self, df):
    return reval.evalr(self.equation, df)
  
  @property
  def equation(self):
    '''Return a tree that represents the model equation.'''
    def parse(text, regexp):
      ## Quote string that consit of a term name + factor/categorical
      ## value so the parser doesn't get confused.  The tree walker in
      ## the parser will automatically remove the quotes.
      new_text = regexp.sub(lambda x: '"' + x.group(0) + '"', text)
      nodes = rparser.parse(new_text)
      return nodes

    if not self._equation:
      categoricals = filter(lambda c: self.frame()[c].dtype, self.frame())
      regexp = re.compile('((' + '|'.join(categoricals) + ')[^:(*)^%$:~]+)')
      prods = [Node(Operator('*'), (parse(x[0], regexp), x[1]))
               for x in self.fixef().itertuples()]
      ## FIXME: Add inverse link function?
      root = Node(Operator('+'), prods)
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

  @property
  def hstab(self):
    frame = self.frame()
    categoricals = frame.select_dtypes(include=['category']).columns
    regexp = re.compile('((' + '|'.join(categoricals) + ')(.*))')
    res = {}
    for k, v in self.stab.items():
      m = regexp.match(k)
      if m:
        cat = m.group(2)
        level = m.group(3)
        if cat in res:
          if level in res[cat]:
            import pdb; pdb.set_trace()
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
    fm = self.call_method('formula')
    formula = re.sub('\s+', ' ', fm.r_repr())
    lhs, _ = formula.split('~')
    return re.sub(r'[ \-.$]', '_', lhs.strip())

  
