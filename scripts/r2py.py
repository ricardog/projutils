#!/usr/bin/env python3

import os
import re
import rpy2.robjects as robjects
import sys

from ..r2py import glm
from ..r2py import lmermod
from ..r2py import glmermod
from .. import predicts
from .. import utils

def doit(obj):
  if 'lmerMod' in obj.rclass:
    mod = lmermod.LMerMod(obj)
  elif 'glmerMod' in obj.rclass:
    mod = glmermod.GLMerMod(obj)
  elif 'glm' in obj.rclass or 'lm' in obj.rclass:
    mod = glm.GLM(obj)
  else:
    print('Skipping object of type %s' % str(obj.rclass))
    return None
  predicts.predictify(mod)
  return mod

def main():
  if len(sys.argv) != 2:
    print("Usage: %s <models.rds>" % os.path.basename(sys.argv[0]))
    sys.exit(1)

  fname = sys.argv[1]
  name = os.path.basename(fname)
  base = os.path.splitext(name)[0]
  pname = re.sub(r'[ \-.$]', '_', base)
  outdir = os.path.dirname(fname)

  print('%s:' % name)
  with open(os.path.join(outdir, base + '.py'), 'w') as ofile:
    obj = robjects.r('models <- readRDS("%s")' % fname)
    if 'list' in obj.rclass:
      for mm in obj.items():
        print("  %s" % mm[0])
        mod = doit(mm[1])
        if mod:
          ofile.write(mod.to_numba(mm[0]))
    else:
      mod = doit(obj)
      if mod:
        ofile.write(mod.to_numba(pname))
