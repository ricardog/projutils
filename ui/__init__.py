
import re

def intensities():
    return ['minimal', 'light', 'intense']
    
def _predictify(sym, prefix):
  newr = sym.replace(prefix, '')
  newr = re.sub(r'(Minimal|Light|Intense) use',  "\\1", newr)
  newr = newr.lower()
  assert newr in intensities(), 'unknown use intensity %s' % sym
  return newr

def predictify(root, prefix):
  if isinstance(root, str) and re.match(prefix, root):
    newr = _predictify(root, prefix)
    return newr
  return root
