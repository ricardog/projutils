#!/usr/bin/env python

import click
from joblib import memory
import numpy as np
import numpy.ma as ma
import os
import pandas as pd
import tempfile

from .. import tiff_utils
from .. import utils

memcache = memory.Memory(cachedir=tempfile.mkdtemp(prefix='hpd-wpp'),
                         verbose=0, mmap_mode='r')

class WPP(object):
  def __init__(self, trend, year, fname):
    self._trend = 'historical' if year < 2011 else trend
    self._year = year
    self._fname = fname
    self._sheet = get_sheets(self._trend, fname)[0]
    if year not in get_years(self.sheet):
      raise RuntimeError('year %d not available in trend %s projection' %
                         (year, trend))
    return

  @property
  def year(self):
    return self._year

  @property
  def trend(self):
    return self._trend

  @property
  def sheet(self):
    return self._sheet

  @property
  def syms(self):
    return ['un_code', 'hpd_ref']

  def eval(self, df):
    return project(self.trend, self.sheet, df['un_code'], df['hpd_ref'],
                   None, self.year, np.nan)

def remap(what, table, nomatch=None):
  f = np.vectorize(lambda x: table[x] if x in table else nomatch,
                   otypes=[np.float32])
  shape = what.shape
  tmp = f(what.flatten())
  return tmp.reshape(*shape)

def check_years(sheet, years):
  if years is None:
    return set()
  available = set(sheet.iloc[14,5:].astype(int).tolist())
  yset = set(years)
  return yset - available

@memcache.cache
def get_sheets(trend, wpp):
  trend = 'estimates' if trend == 'historical' else trend
  xls = pd.ExcelFile(wpp)
  if trend == 'all':
    names = filter(lambda x: x != u'NOTES', xls.sheet_names)
  else:
    assert trend.upper() in xls.sheet_names
    names = [trend.upper()]
  sheets = [pd.read_excel(wpp, name) for name in names]
  for name, sheet in zip(names, sheets):
    ## FIXME: I store the name of the sheet (or tab) in cell (0, 0)
    ## becuase memcache will not preserve metadata attributes.  Once
    ## this gets fixed in pandas, it would be cleaner to create an
    ## attribute (name) that stores the sheet name.
    sheet.ix[0, 0] = name.lower()
  return sheets

def get_years(sheet):
  return sheet.iloc[14,5:].astype(int).tolist()
  
def project(trend, sheet, countries, grumps, mask, year, nodata):
  ## Some of the cells representing the year are treated as strings and
  ## some as integers so check for both.
  col = np.logical_or(sheet.iloc[14].isin([year]),
                      sheet.iloc[14].isin([str(year)]))
  if not np.any(col):
    raise ValueError
  ccode = sheet.iloc[15:,4].astype(int).tolist()
  hist = sheet.ix[15:, col]
  if trend == 'historical':
    ref = sheet.ix[15:,u'Unnamed: 57']
  else :
    ref = sheet.ix[15:,u'Unnamed: 5']
  pop = hist.divide(ref, axis="index").astype('float32').values

  mydict = dict((v, pop[ii]) for ii, v in enumerate(ccode))
  growth = remap(countries, mydict, nodata)
  unknown_mask = np.where(growth == nodata, True, False)
  if mask:
    my_mask = np.logical_or(mask, unknown_mask)
  else:
    my_mask = unknown_mask
  new_pop = np.multiply(grumps, growth)
  return np.where(my_mask, nodata, new_pop)

def regularize(*args):
  tiff_utils.regularize(args)
