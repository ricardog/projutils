import six
from rpy2.robjects.methods import RS4Auto_Type

import projections.r2py.mermod as mermod
import projections.r2py.lmermod as lmermod

@six.add_metaclass(RS4Auto_Type)
class GLMerMod(mermod.MerMod):
  __rname__ = 'glmerMod'
  __rpackagename__ = 'lme4'
  def call_method(self, what):
    try:
      super(GLMerMod, self).call_method(what)
    except AttributeError as e:
      method = getattr(self.pkg, what + '_' + lmermod.LMerMod.__rname__)
    return method(self)
