
import re

LU = {'primary': 'primf',
      'secondary': 'secd',
      'cropland': 'c3ann + c4ann + c3nfx',
      'pasture': 'pastr + range',
      'urban': 'urban',
      'plantation_pri': 'c3per + c4per',
      'plantation_sec': '0',
}

LUp3 = {'primary': 'primf',
        'young_secondary': 'secdy',
        'intermediate_secondary': 'secdi',
        'mature_secondary': 'secdm',
        'cropland': 'c3ann + c4ann + c3nfx',
        'pasture': 'pastr + range',
        'urban': 'urban',
        'plantation_pri': 'c3per + c4per',
        'plantation_sec': '0',
}

def types(plus3=False):
  if plus3:
    return sorted(LUp3.keys())
  return sorted(LU.keys())

def _predictify(root, prefix):
  newr = root.replace(prefix, '')
  newr = newr.replace(' Vegetation', '')
  newr = newr.replace(' vegetation', '')
  newr = newr.replace(' forest', '_pri')
  newr = re.sub(r'(Mature|Intermediate|Young)',  "\\1", newr)
  newr = newr.replace(' ', '_')
  newr = newr.lower()
  assert newr in types() or newr in types(True), 'unknown land use type %s' % root
  return newr

def is_luh5(syms, prefix):
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
