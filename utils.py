
import argparse
import errno
import os
import platform
from pylru import lrudecorator
import re
import subprocess
import sys
import threading
import time

class FullPaths(argparse.Action):
  """Expand user- and relative-paths"""
  def __call__(self, parser, namespace, values, option_string=None):
    setattr(namespace, self.dest, os.path.abspath(os.path.expanduser(values)))

def is_dir(dirname):
  """Checks if a path is an actual directory"""
  if not os.path.isdir(dirname):
    msg = "{0} is not a directory".format(dirname)
    raise argparse.ArgumentTypeError(msg)
  else:
    return dirname

def mkpath(path):
  try:
    os.makedirs(path)
  except OSError as exc:  # Python >2.5
    if exc.errno == errno.EEXIST and os.path.isdir(path):
      pass
    else:
      raise

@lrudecorator(10)
def outdir(db=None):
  cmd = ['make', 'outdir']
  if db is not None:
    cmd.append('DIVERSITY_DB=%s' % db)
  return subprocess.check_output(cmd, shell=False).split('\n')[0]

def data_root():
  if platform.node() == 'vagrant':
    dr = '/data'
  elif 'DATA_ROOT' not in os.environ:
    if os.path.isdir('../../data'):
      dr = '../../data'
      os.environ['DATA_ROOT'] = os.path.abspath(dr)
    else:
      raise RuntimeError('please set DATA_ROOT')
  else:
    dr = os.environ['DATA_ROOT']
  return os.path.abspath(dr)

def gdp_csv():
  return os.path.join(data_root(), 'econ',
                      'gdp-per-capita.csv')

def cpi_csv():
  return os.path.join(data_root(), 'econ',
                      'cpi.csv')

def wpp_xls():
  return os.path.join(data_root(), 'wpp',
                      'WPP2010_DB2_F01_TOTAL_POPULATION_BOTH_SEXES.xls')

def luh2_prefix():
  return 'LUH2_v2f_beta_'

def luh2_dir():
  return os.path.join(data_root(), 'luh2_v2')

def luh2_scenarios():
  scenarios = filter(lambda p: (p == 'historical' or
                                p[0:17] == 'LUH2_v2f_beta_SSP'),
                     os.listdir(luh2_dir()))
  return tuple(re.sub('^' + luh2_prefix(), '', x).lower()
               for x in scenarios)

def luh2_scenario_ssp(scenario):
  ssp, rcp, iam = scenario.split('_')
  return ssp

def _luh2_file(scenario, fname):
  if scenario == 'historical':
    return os.path.join(luh2_dir(), scenario, fname)
  return os.path.join(luh2_dir(), luh2_prefix() + scenario.upper(),
                      fname)

def luh2_static(what=None):
  if what:
    return 'NETCDF:' + os.path.join(luh2_dir(), 'staticData_quarterdeg.nc:%s' % what)
  return os.path.join(luh2_dir(), 'staticData_quarterdeg.nc')

def luh2_states(scenario):
  return _luh2_file(scenario, 'states.nc')

def luh2_transitions(scenario):
  return _luh2_file(scenario, 'transitions.nc')

def luh2_management(scenario):
  return _luh2_file(scenario, 'management.nc')

def grumps1():
  return os.path.join(data_root(), 'grump1.0', 'gluds00ag')

def grumps4():
  return os.path.join(data_root(), 'grump4.0',
                      'gpw-v4-population-density-adjusted-to-2015-' +
                      'unwpp-country-totals_2015.tif')

def sps(scenario, year):
  path = os.path.join(utils.data_root(), 'sps',
                      '%s_NetCDF' % scenario.upper(),
                      'total/NetCDF')
  name = '%s_%d' % (scenario, year)
  fname = os.path.join(path, "%s.nc" % name)
  return 'netcdf:%s/%s.nc:%s' % (path, name, name)

def run(cmd, sem=None):
  try:
    if sem is None:
      out = subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)
    else:
      with sem:
        out = subprocess.check_output(cmd, shell=False, stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError, e:
    print e.output
    sys.exit(1)
  return out

def run_parallel(cmds, j):
  threads = []
  sem = threading.Semaphore(j)
  for cmd in cmds:
    t = threading.Thread(target=run, args=[cmd, sem])
    threads.append(t)
    t.start()
  return threads
