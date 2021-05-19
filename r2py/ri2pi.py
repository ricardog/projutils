import datetime

import numpy as np
import pandas as pd

import rpy2.robjects as robjects
import rpy2.rinterface as rinterface
from rpy2.robjects import pandas2ri

import pdb


def ri2pi(obj):
    if obj is None:
        return None
    klass = type(obj)
    if klass in (
        robjects.vectors.FloatVector,
        robjects.vectors.IntVector,
        robjects.vectors.BoolVector,
        robjects.vectors.StrVector,
    ):
        vect = np.asarray(obj)
        assert vect.ndim == 1, "R vector has more than 1 dimension"
        if "Date" in tuple(obj.rclass):
            origin = datetime.date(1970, 1, 1)
            vect = tuple(map(lambda v: origin + datetime.timedelta(int(v)), vect))
        if obj.names == rinterface.NULL:
            # Unnamed vector, return data as np array or as a scalar
            res = vect[0] if len(vect) == 1 else vect
        else:
            # For named vectors return a pandas.DataFrame
            res = pd.DataFrame(vect, index=map(str, obj.names),
                               columns=["value"])
    elif klass == robjects.vectors.ListVector:
        res = dict((t[0], ri2pi(t[1])) for t in obj.items())
    elif klass == robjects.vectors.StrVector:
        raise RuntimeError
    elif klass == robjects.vectors.FactorVector:
        values = map(lambda v: 0 if v[1] == obj.NAvalue else v[1], obj.items())
        res = pandas.Categorical.from_codes(
            numpy.asarray(tuple(values)) - 1,
            categories=obj.do_slot("levels"),
            ordered="ordered" in obj.rclass,
        )
    elif klass == robjects.Formula:
        res = obj
    elif klass == rinterface.NULLType:
        res = None
    elif klass == robjects.vectors.Vector:
        res = obj
    elif klass == robjects.vectors.DataFrame:
        standard = True
        try:
            # res = pandas2ri.ri2py(obj)
            standard = False
        except ValueError as e:
            standard = False
        if not standard:
            res = pd.DataFrame()
            for item in obj.items():
                name = str(item[0])
                klasses = tuple(item[1].rclass)
                if "numeric" in klasses or "integer" in klasses or "matrix" in klasses:
                    mat = np.asarray(item[1])
                    assert mat.ndim in [
                        1,
                        2,
                    ], "unexpected n-dimensional array in data.frame"
                    if mat.ndim > 1:
                        for idx in range(mat.shape[1]):
                            res[name + str(idx + 1)] = mat[:, idx]
                    else:
                        res[name] = mat
                elif "factor" in klasses:
                    res[name] = pandas2ri.rpy2py(item[1])
                elif "logical" in klasses:
                    res[name] = pandas2ri.rpy2py(item[1])
                elif "Date" in klasses:
                    # raise RuntimeError('untested Date conversion')
                    origin = datetime.date(1970, 1, 1)
                    res[name] = tuple(
                        map(lambda v: origin + datetime.timedelta(int(v)), item[1])
                    )
                else:
                    raise RuntimeError("unknown data class %s" % klasses)
    elif klass == robjects.vectors.Matrix:
        res = np.array(obj)
    else:
        raise RuntimeError("unknown object type '%s'" % str(klass))
    return res
