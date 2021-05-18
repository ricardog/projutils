#!/usr/bin/env python

import pprint
import rpy2.robjects as robjects

from .. import rds
from .. import lu
from .. import lui

rcp_models = ['out/_d5ed9724c6cb2c78b59707f69b3044e6/ab-model.rds',
              '../models/ab-tropical-forest.rds',
              '../models/ab-islands.rds',
              '../models/ab-mainland.rds',
            ]

luh2_models = ['../models/sr1-model.rds',
               '../models/sr2-model.rds',
               '../models/ab5-model.rds',
               '../models/ab6-model.rds',
               '../models/ab7-model.rds',
               ]

def process(fname, rcp=False, luh2=False):
    print("*** %s" % fname)
    mod = rds.read(fname)
    eqn = mod.equation
    pprint.pprint(eqn)
    pprint.pprint(mod.stab)
    return

  
if __name__ == '__main__':
    for m in rcp_models:
        process(m, rcp=True, luh2=False)
    for m in luh2_models:
        process(m, rcp=False, luh2=True)
