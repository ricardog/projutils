import rpy2.robjects as robjects
import rpy2.rinterface as rinterface
from rpy2.rinterface import baseenv
from rpy2.rinterface import SexpS4
from rpy2.rinterface import StrSexpVector
from rpy2.robjects import default_converter
from rpy2.robjects import pandas2ri
from rpy2.robjects.conversion import Converter
from rpy2.robjects.conversion import localconverter

from . import lmermod
from . import glmermod


def ri2ro_s4(obj):
    if "lmerMod" in obj.rclass:
        res = lmermod.LMerMod(obj)
    elif "glmerMod" in obj.rclass:
        res = glmermod.GLMerMod(obj)
    else:
        res = obj
    return res


def read(path):
    pandas2ri.activate()
    rpath = StrSexpVector((path,))
    readrds = baseenv["readRDS"]
    my_converter = Converter("lme4-aware converter", template=default_converter)
    my_converter.ri2ro.register(SexpS4, ri2ro_s4)
    with localconverter(my_converter) as cv:
        obj = robjects.r("readRDS('%s')" % path)
    if isinstance(obj, lmermod.LMerMod) or isinstance(obj, glmermod.GLMerMod):
        return obj
    else:
        return robjects.conversion.ri2py(obj)


def save(obj, path):
    save_rds = robjects.r("saveRDS")
    save_rds(obj, path)
