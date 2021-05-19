import six
from rpy2.robjects.methods import RS4Auto_Type
from . import mermod


@six.add_metaclass(RS4Auto_Type)
class LMerMod(mermod.MerMod):
    __rname__ = "merMod"
    __rpackagename__ = "lme4"
