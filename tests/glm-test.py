#!/usr/bin/env python

import pprint
import rpy2.robjects as robjects
import sys
import time

import env
import glm

print("starting")
stime = time.time()
fname = sys.argv[1] if len(sys.argv) > 1 else "out/_d5ed9724c6cb2c78b59707f69b3044e6/cropland.rds"
models = robjects.r('models <- readRDS("%s")' % fname)
mod = glm.GLM(models[0])
print("parsed rds file")
rtime = time.time()
eqn = mod.equation
etime = time.time()
stab = mod.stab
ztime = time.time()

#pprint.pprint(mod.coefficients())
pprint.pprint(eqn)
pprint.pprint(stab)

print("read : %6.2f" % (rtime - stime))
print("eqn  : %6.2f" % (etime - rtime))
print("sym  : %6.2f" % (ztime - etime))
print("total: %6.2f" % (ztime - stime))

