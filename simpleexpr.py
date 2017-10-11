
import numpy as np
import numpy.ma as ma

import r2py.eval as myeval
import r2py.rparser as rparser

class SimpleExpr():
  def __init__(self, name, expr):
    self.name = name
    self.tree = myeval.make_inputs(rparser.parse(expr))
    lokals = {}
    exec myeval.to_py(self.tree, name) in lokals
    self.func = lokals[name + '_st']

  @property
  def syms(self):
    return myeval.find_inputs(self.tree)
  
  def eval(self, df):
    try:
      res = self.func(df)
    except KeyError, e:
      print "Error: input '%s' not defined" % e
      raise e
    if not isinstance(res, np.ndarray):
      res = ma.masked_array(np.full(df.values()[0].shape, res,
                                    dtype=np.float32))
    return res
