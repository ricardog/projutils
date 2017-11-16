
from copy import copy
import importlib
import numpy as np
import re
import os
import sys

from .. import lu
from .. import utils

LUI_MODEL_MAP = {'annual': 'cropland',
                 'nitrogen': 'cropland',
                 'cropland': 'cropland',
                 'pasture': 'pasture',
                 'perennial': 'cropland',
                 'primary': 'primary',
                 'rangelands': 'pasture',
                 'timber': 'cropland',
                 'urban': 'urban',
                 'young_secondary': 'secondary',
                 'intermediate_secondary': 'secondary',
                 'mature_secondary': 'secondary',
}

def model(name):
  return LUI_MODEL_MAP[name]

class LUH2(object):
  def __init__(self, name, intensity):
    self._name = name
    self._intensity = intensity
    self._inputs = []
    mod_name = model(name)
    py = os.path.join(utils.lui_model_dir(), '%s.py' % mod_name)
    if not os.path.isfile(py):
      raise RuntimeError('could not find python module for %s' % mod_name)
    rds = os.path.join(utils.lui_model_dir(), '%s.rds' % mod_name)
    if not os.path.isfile(rds):
      raise RuntimeError('could not find RDS file for %s' % mod_name)
    if os.path.getmtime(py) < os.path.getmtime(rds):
      raise RuntimeError('python module is older than RDS file for %s' % name)
    if intensity != 'minimal':
      if utils.lui_model_dir() not in sys.path:
        sys.path.append(utils.lui_model_dir())
      self._pkg = importlib.import_module(mod_name)
      self._pkg_func = getattr(self._pkg, intensity)
      self._pkg_inputs = getattr(self._pkg, 'inputs')()
      self._inputs += [name if x == mod_name else x for x in self._pkg_inputs]
      self._finputs = copy(self._inputs)
      self._inputs += [name + '_' + intensity + '_ref']
      def myfunc(df):
        args = [df[arg] for arg in self._finputs]
        return self._pkg_func(*args)
      self._func = myfunc
    if intensity == 'light':
      self._inputs += [name + '_intense']
    elif intensity == 'minimal':
      self._inputs += [name + '_intense', name + '_light']
    
  @property
  def name(self):
    return self._name + '_' + self.intensity
    
  @property
  def as_intense(self):
    return self._name + '_intense'
    
  @property
  def as_light(self):
    return self._name + '_light'
    
  @property
  def as_minimal(self):
    return self._name + '_minimal'
    
  @property
  def intensity(self):
    return self._intensity
    
  @property
  def syms(self):
    return self._inputs

  def eval(self, df):
    if self.intensity == 'minimal':
      res = (df[self._name] - df[self.as_intense] - df[self.as_light])
      return res
    res = self._func(df)
    res[np.where(np.isnan(res))] = 1.0
    res = np.clip(df[self.name + '_ref'] + res, 0, 1)
    if self.intensity == 'light':
      intense = df[self.as_intense] / (df[self._name] + 1e-10)
      res = np.where(intense + res > 1, 1 - intense, res)
    res *= df[self._name]
    return res

def _predictify(sym, prefix):
  newr = sym.replace(prefix, '')
  newr = newr.replace(' vegetation', '')
  newr = newr.replace(' forest', '_pri')
  newr = newr.replace('Managed ', '')
  newr = newr.replace(' secondary', '_secondary')
  newr = re.sub(r'(Minimal|Light|Intense) use',  "\\1", newr)
  newr = newr.lower()
  name = newr.split(' ')[0]
  newr = newr.replace(' ', '_')
  newr = newr.replace('pasture_light', 'pasture_minimal_and_light')
  newr = newr.replace('rangelands_light', 'rangelands_light_and_intense')
  assert name in lu.luh2.types(), 'unknown land use type %s' % sym
  return newr

def is_luh2(syms, prefix):
  for sym in syms:
    try:
      newr = _predictify(sym, prefix)
    except AssertionError as e:
      return False
  return True

def predictify(root, prefix):
  if isinstance(root, str) and re.match(prefix, root):
    newr = _predictify(root, prefix)
    return newr
  return root
