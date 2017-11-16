
import re

from ..r2py import reval as reval
from ..r2py import rparser

LU = {'annual': 'c3ann + c4ann',
      'nitrogen': 'c3nfx',
      'cropland': 'c3ann + c3ann + c3nfx',
      'pasture': 'pastr',
      'perennial': 'c3per + c4per',
      'primary': 'primf + primn',
      'rangelands': 'range',
      'timber': '0',
      'urban': 'urban',
      'young_secondary': 'secdy',
      'intermediate_secondary': 'secdi',
      'mature_secondary': 'secdm',
}

funcs = {}
symbols = {}
trees = {}

def types():
  return sorted(LU.keys())

def expr(lu):
  if lu not in LU:
    raise ValueError("unknown land use type: '%s'" % lu)
  return LU[lu]

def tree(lu):
  if lu not in trees:
    trees[lu] = reval.make_inputs(rparser.parse(expr(lu)))
  return trees[lu]
  
def func(lu):
  if lu not in funcs:
    lokals = {}
    exec(reval.to_py(tree(lu), lu), None, lokals)
    funcs[lu] = lokals[lu + '_st']
  return funcs[lu]

def syms(lu):
  if lu not in symbols:
    root = tree(lu)
    symbols[lu] = reval.find_inputs(root)
  return symbols[lu]
  
def is_luh2(syms, prefix):
  for sym in syms:
    newr = _predictify(sym, prefix)
    if not newr in types():
      return False
  return True

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
  assert name in types(), 'unknown land use type %s' % sym
  return newr

def is_luh2(syms, prefix):
  for sym in syms:
    try:
      newr = _predictify(sym, prefix)
    except AssertionError as e:
      return False
  return True

def as_contrast(root, prefix):
  if isinstance(root, str) and re.match(prefix, root):
    #import pdb; pdb.set_trace()
    newr = root.replace(prefix, '')
    newr = re.sub(r'^.*-',  '', newr)
    newr = newr.replace('Managed ', '')
    newr = newr.replace(' Minimal', '')
    return _predictify(newr, '')
  return root

def predictify(root, prefix):
  if isinstance(root, str) and re.match(prefix, root):
    newr = _predictify(root, prefix)
    return newr
  return root
