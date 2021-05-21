import importlib
import numpy as np
import os
import sys

from .. import utils


class OneKm(object):
    def __init__(self, name, intensity):
        self._name = name
        self._intensity = intensity
        self._inputs = []
        if name in ["plantation_pri", "plantation_sec"]:
            raise RuntimeError("unexpected lu type %s" % name)

        py = os.path.join(utils.lui_model_dir(), "%s.py" % name)
        if not os.path.isfile(py):
            raise RuntimeError("could not find python module for %s" % name)
        rds = os.path.join(utils.lui_model_dir(), "%s.rds" % name)
        if not os.path.isfile(rds):
            raise RuntimeError("could not find RDS file for %s" % name)
        if os.path.getmtime(py) < os.path.getmtime(rds):
            raise RuntimeError("python module is older than RDS file for %s" % name)
        if intensity != "minimal":
            if utils.lui_model_dir() not in sys.path:
                sys.path.append(utils.lui_model_dir())
            self._pkg = importlib.import_module(name)
            self._pkg_func = getattr(self._pkg, intensity + "_st")
            self._inputs += getattr(self._pkg, "inputs")()
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
        return self._name + "_minimal"

    @property
    def intensity(self):
        return self._intensity

    @property
    def syms(self):
        return self._inputs

    def eval(self, df):
        if self._name in ["plantation_pri", "plantation_sec"]:
            return df[self._name] / 3
        if self._name[-10:] == "_secondary":
            return ma.where(
                df["secondary"] <= 0,
                0,
                df["secondary_" + self.intensity]
                * df[self._name]
                / (df["secondary"] + 1e-5),
            )
        if self.intensity == "minimal":
            res = df[self._name] - df[self.as_intense] - df[self.as_light]
            return res
        res = self._pkg_func(df)
        res[np.where(np.isnan(res))] = 1.0
        res = np.clip(res, 0, 1)
        if self.intensity == "light":
            intense = df[self.as_intense] / (df[self._name] + 1e-10)
            res = np.where(intense + res > 1, 1 - intense, res)
        res *= df[self._name]
        return res
