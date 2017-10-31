#!/usr/bin/env python

import os
import rpy2.robjects as robjects
import sys

import env
import glm
import rds
import utils

lus = ['cropland', 'pasture', 'primary', 'secondary', 'urban']
lus = ['cropland']
model_dir = utils.lui_model_dir()

name = 'sr1-model'
fname = "../models/%s.rds" % name
mod = rds.read(fname)
with open(os.path.join(model_dir, name + '_nb.py'), 'w') as ofile:
  pass
  #ofile.write(mod.to_numba(name))

for lu in lus:
  print('%s:' % lu)
  with open(os.path.join(model_dir, lu + '_nb.py'), 'w') as ofile:
    fname = "out/_d5ed9724c6cb2c78b59707f69b3044e6/%s.rds" % lu
    models = robjects.r('models <- readRDS("%s")' % fname)
    for mm in models.items():
      print("  %s" % mm[0])
      mod = glm.GLM(mm[1])
      ofile.write(mod.to_numba(mm[0]))
