import importlib
import numpy as np
import numpy.ma as ma
import os
import sys

from .rcp import RCP                                        # noqa F401
from .luh2 import LUH2                                      # noqa F401
from .luh5 import LUH5                                      # noqa F401
from .onekm import OneKm                                    # noqa F401
from .. import utils

def intensities():
    return ('minimal', 'light', 'intense')


class LUI(object):
    def __init__(self, name, intensity, mod_name):
        self._name = name
        self._mod_name = mod_name
        self._intensity = intensity
        self._inputs = []
        py = os.path.join(utils.lui_model_dir(), "%s.py" % mod_name)
        if not os.path.isfile(py):
            raise RuntimeError("could not find python module for %s" % mod_name)
        rds = os.path.join(utils.lui_model_dir(), "%s.rds" % mod_name)
        if not os.path.isfile(rds):
            raise RuntimeError("could not find RDS file for %s" % mod_name)
        if os.path.getmtime(py) < os.path.getmtime(rds):
            raise RuntimeError(
                "python module is older than RDS file for %s" % mod_name
            )
        if intensity != "minimal":
            if utils.lui_model_dir() not in sys.path:
                sys.path.append(utils.lui_model_dir())
            self._pkg = importlib.import_module(mod_name)
            self._pkg_func = getattr(self._pkg, intensity)
            inputs = getattr(self._pkg, "inputs")()
            self._inputs += list(set(inputs) - {mod_name}) + [name]
        if intensity == "light":
            self._inputs += [name + "_intense"]
        elif intensity == "minimal":
            self._inputs += [name + "_intense", name + "_light"]

    @property
    def name(self):
        return self._name + "_" + self.intensity

    @property
    def as_intense(self):
        return self._name + "_intense"

    @property
    def as_light(self):
        return self._name + "_light"

    @property
    def as_minimal(self):
        return self.intensity == "minimal"

    @property
    def is_intense(self):
        return self.intensity == "intense"

    @property
    def is_light(self):
        return self.intensity == "light"

    @property
    def is_minimal(self):
        return self.intensity == "minimal"

    @property
    def intensity(self):
        return self._intensity

    @property
    def inputs(self):
        return self._inputs  # FIXME: + [self.name + '_ref']

    def __repr__(self):
        return f"f({', '.join(self.inputs)})"

    def eval(self, df):
        if self.is_minimal:
            res = df[self._name] - df[self.as_intense] - df[self.as_light]
            return res
        res = self._pkg_func(**{self._mod_name: df[self._name],
                                "hpd": df["hpd"], "unSub": df["unSub"]})
        res[np.where(np.isnan(res))] = 1.0
        res = np.clip(res, 0, 1)
        if self.intensity == "light":
            intense = df[self.as_intense] / (df[self._name] + 1e-10)
            res = np.where(intense + res > 1, 1 - intense, res)
        res *= df[self._name]
        return res
