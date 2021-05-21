#!/usr/bin/env python

import os
import pprint
import sys

import env
import rds

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("give me somthing to do")
        sys.exit()
    fname = os.path.join(os.getcwd(), sys.argv[1] + ".rds")
    if not os.path.isfile(fname):
        print("%s doesn't exist" % fname)
        sys.exit()
    print("reading %s" % fname)
    model = rds.read(fname)
    eqn = model.equation
    pprint.pprint(eqn)
    eqn_vars = model.stab
    pprint.pprint(eqn_vars)
