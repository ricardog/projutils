#!/usr/bin/env python

import os
import rpy2.robjects as robjects

import env
import glm
import utils

lus = ['cropland', 'pasture', 'primary', 'secondary', 'urban']
model_dir = utils.lui_model_dir()

for lu in lus:
  print('%s:' % lu)
  with open(os.path.join(model_dir, lu + '.py'), 'w') as ofile:
    fname = "out/_d5ed9724c6cb2c78b59707f69b3044e6/%s.rds" % lu
    models = robjects.r('models <- readRDS("%s")' % fname)
    for mm in models.items():
      print("  %s" % mm[0])
      mod = glm.GLM(mm[1])
      ofile.write(mod.to_py(mm[0]))
