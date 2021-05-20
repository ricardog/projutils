
from r2py import reval as reval
from r2py import rparser

LU = {'annual': 'c3ann + c4ann',
      'nitrogen': 'c3nfx',
      'cropland': 'c3ann + c4ann',
      'pasture': 'pastr',
      'perennial': 'c3per + c4per',
      'primary': 'primf + primn',
      'rangelands': 'range',
      'timber': 0,
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
