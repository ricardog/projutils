
import netCDF4
import os
import sys

from rasterset import Raster
from simpleexpr import SimpleExpr
import hpd
import lu
import lui
import ui
import utils

def rcp(scenario, year, hpd_trend):
  rasters = {}

  lus = [SimpleExpr('primary', 'gothr - gfvh1 - gfvh2'),
         SimpleExpr('secondary', 'max(gsecd - gfsh1 - gfsh2 - gfsh3, 0)'),
         SimpleExpr('cropland', 'gcrop'),
         SimpleExpr('pasture', 'gpast'),
         SimpleExpr('urban', 'gurbn'),
         SimpleExpr('plantation_pri', 'min(gothr, gfvh1 + gfvh2)'),
         SimpleExpr('plantation_sec', 'min(gsecd, gfsh1 + gfsh2 + gfsh3)'),
  ]

  ## Human population density and UN subregions
  rasters['hpd_ref'] = Raster('hpd_ref', 'ds/rcp/gluds00ag.tif')
  rasters['unSub'] = Raster('unSub', 'ds/rcp/un_subregions.tif')
  rasters['un_code'] = Raster('un_codes', 'ds/rcp/un_codes.tif')
  rasters['hpd'] = hpd.WPP(hpd_trend, year, utils.wpp_xls())

  ## NOTE: Pass max & min of log(HPD) so hi-res rasters can be processed
  ## incrementally.  Recording the max value here for when I create
  ## other functions for other resolutions.
  ## 0.50 =>  20511.541 / 9.92874298232494
  ## 0.25 =>  41335.645 / 10.62948048177454
  ## 1km  => 872073.500 / 13.678628988329825
  rasters['logHPD_rs'] = SimpleExpr('logHPD_rs',
                                    'scale(log(hpd + 1), 0.0, 1.0, 0.0, 9.93)')
  rasters['logDistRd_rs'] = Raster('logDistRd_rs',
                                   'ds/rcp/roads-final.tif')

  ## Inputs RCP rasters
  names = tuple(set(reduce(lambda x,y: x + y, [lu.syms for lu in lus], [])))
  
  for name in names:
    path = 'ds/lu/rcp/%s/updated_states/%s.%d.tif' % (scenario, name, year)
    rasters[name] = Raster(name, path)

  ## Land use intensity rasters
  for lu in lus:
    rasters[lu.name] = lu
    ref_path = 'ds/rcp/%s-recal.tif' % lu.name
    for band, intensity in enumerate(lui.intensities()):
      n = lu.name + '_' + intensity
      rasters[n] = lui.RCP(lu.name, intensity)
      n2 = n + '_ref'
      if lu.name[0:11] == 'plantation_':
        rasters[n2] = SimpleExpr(n2, '0')
      else:
        rasters[n2] = Raster(n2, ref_path, band + 1)
  return rasters


def luh5(scenario, year, plus3):
  rasters = {}

  lus = [SimpleExpr('primary', 'primf + primn'),
         SimpleExpr('cropland', 'c3ann + c4ann + c3nfx'),
         SimpleExpr('pasture', 'range + pastr'),
         SimpleExpr('plantation_pri', 'c3per + c4per'),
         SimpleExpr('plantation_sec', '0'),
  ]

  if plus3:
    lus += [SimpleExpr('secondary', 'mature_secondary + intermediate_secondary + young_secondary'),
            SimpleExpr('mature_secondary', 'secdmf + secdmn'),
            SimpleExpr('intermediate_secondary', 'secdif + secdin'),
            SimpleExpr('young_secondary', 'secdyf + secdyn'),
    ]
  else:
    lus += [SimpleExpr('secondary', 'secdf + secdn')]
    
  ## Human population density and UN subregions
  rasters['unSub'] = Raster('unSub', 'ds/luh5/un_subregions.tif')
  rasters['un_code'] = Raster('un_codes', 'ds/luh5/un_codes.tif')
  #rasters.update(hpd.sps.raster(ssp, year))
  if year <= 2010:
    rasters['hpd_ref'] = Raster('hpd_ref', 'ds/luh5/gluds00ag.tif')
    rasters['hpd'] = hpd.WPP('historical', year, utils.wpp_xls())
  else:
    rasters.update(hpd.sps.scale_grumps(utils.luh2_scenario_ssp(scenario),
                                        year))
  ## The values in the expression of hpd_max need to be updated when the
  ## predicts DB changes.
  rasters['hpd_max'] = SimpleExpr('hpd_max',
                                  '(primary * 39.810) + (cropland * 125.40) + (pasture * 151.500) + (plantation_pri * 140.70) + (secondary * 98.400) + (urban * 2443.0)')

  ## NOTE: Pass max & min of log(HPD) so hi-res rasters can be processed
  ## incrementally.  Recording the max value here for when I create
  ## other functions for other resolutions.
  ## 0.50 =>  20511.541 / 9.92874298232494
  ## 0.25 =>  41335.645 / 10.62948048177454 (10.02 for Sam)
  ## 1km  => 872073.500 / 13.678628988329825
  maxHPD = 10.02083
  rasters['logHPD_rs'] = SimpleExpr('logHPD_rs',
                                    'scale(log(hpd + 1), 0.0, 1.0, 0.0, %f)' %
                                    maxHPD)

  fname = utils.luh2_states(scenario)
  for fname in (utils.luh2_states(scenario),
                'ds/luh2/secd-' + scenario + '.nc'):
    try:
      ds = netCDF4.Dataset(fname)
    except IOError, e:
      print "Error: opening '%s'" % fname
      raise IOError("Error: opening '%s'" % fname)
    ds_vars = set(ds.variables.keys())
    names = set(reduce(lambda x,y: x + y, [lu.syms for lu in lus], ['urban']))
    for name in set.intersection(names, ds_vars):
      band = year - 849 if scenario == 'historical' else year - 2014
      rasters[name] = Raster(name, "netcdf:%s:%s" % (fname, name),
                             band = band)

  for lu in lus:
    rasters[lu.name] = lu
    ref_path = 'ds/luh5/%s-recal.tif' % lu.name
    for band, intensity in enumerate(lui.intensities()):
      n = lu.name + '_' + intensity
      rasters[n] = lui.LUH5(lu.name, intensity)
      n2 = n + '_ref'
      if lu.name[0:11] == 'plantation_':
        rasters[n2] = SimpleExpr(n2, '0')
      elif lu.name[-10:] != '_secondary':
        rasters[n2] = Raster(n2, ref_path, band + 1)

  for band, intensity in enumerate(lui.intensities()):
    n = 'urban_' + intensity
    rasters[n] = lui.LUH5('urban', intensity)
    n2 = n + '_ref'
    rasters[n2] = Raster(n2, 'ds/luh5/urban-recal.tif', band + 1)

  return rasters


def luh2(scenario, year, fnf):
  rasters = {}
  if scenario not in utils.luh2_scenarios():
    raise ValueError('Unknown scenario %s' % scenario)
  ssp = scenario[0:4]
  
  if fnf not in ('f', 'n'):
    raise ValueError('Pass f => forested / n => non-forested')
  
  lus = [SimpleExpr('annual', 'c3ann + c4ann'),
         SimpleExpr('nitrogen', 'c3nfx'),
         SimpleExpr('pasture', 'pastr'),
         SimpleExpr('perennial', 'c3per + c4per'),
         SimpleExpr('primary', 'prim' + fnf),
         SimpleExpr('rangelands', 'range'),
         SimpleExpr('timber', '0'),
         SimpleExpr('young_secondary', 'secdy' + fnf),
         SimpleExpr('intermediate_secondary', 'secdi' + fnf),
         SimpleExpr('mature_secondary', 'secdm' + fnf),
  ]
  rasters['secondary'] = SimpleExpr('secondary',
                                    'young_secondary + intermediate_secondary + mature_secondary')
 
  ## Human population density and UN subregions
  rasters['unSub'] = Raster('unSub', 'ds/luh2/un_subregions.tif')
  rasters['un_code'] = Raster('un_codes', 'ds/luh2/un_codes.tif')
  #rasters.update(hpd.sps.raster(ssp, year))
  if year <= 2010:
    rasters['hpd_ref'] = Raster('hpd_ref', 'ds/luh2/gluds00ag.tif')
    rasters['hpd'] = hpd.WPP('historical', year, utils.wpp_xls())
  else:
    rasters.update(hpd.sps.scale_grumps(ssp, year))

  ## Agricultural suitability
  #rasters['ag_suit'] = Raster('ag_suit', 'ds/luh2/ag-suit-zero.tif')
  rasters['ag_suit'] = Raster('ag_suit', 'ds/luh2/ag-suit-0.tif')
  
  ## NOTE: Pass max & min of log(HPD) so hi-res rasters can be processed
  ## incrementally.  Recording the max value here for when I create
  ## other functions for other resolutions.
  ## 0.50 =>  20511.541 / 9.92874298232494
  ## 0.25 =>  41335.645 / 10.62948048177454 (10.02 for Sam)
  ## 1km  => 872073.500 / 13.678628988329825
  maxHPD = 10.02083 if fnf == 'n' else 9.823253
  rasters['logHPD_rs'] = SimpleExpr('logHPD_rs',
                                    'scale(log(hpd + 1), 0.0, 1.0, 0.0, %f)' %
                                    maxHPD)
  rasters['logDTR_rs'] = Raster('logDTR_rs',
                                'ds/luh2/roads-final.tif')
  for fname in (utils.luh2_states(scenario),
                'ds/luh2/secd-' + scenario + '.nc'):
    try:
      ds = netCDF4.Dataset(fname)
    except IOError, e:
      print "Error: opening '%s'" % fname
      raise IOError("Error: opening '%s'" % fname)
    ds_vars = set(ds.variables.keys())
    names = set(reduce(lambda x,y: x + y, [lu.syms for lu in lus], ['urban']))
    for name in set.intersection(names, ds_vars):
      band = year - 849 if scenario == 'historical' else year - 2014
      rasters[name] = Raster(name, "netcdf:%s:%s" % (fname, name),
                             band = band)

  for lu in lus:
    rasters[lu.name] = lu
    if lu.name in ('annual', 'nitrogen', 'perennial', 'timber'):
      ref_path = 'ds/luh2/%s-recal.tif' % lu.name
    else:
      ref_path = 'ds/luh2/%s-recal.tif' % lu.syms[0]
    for band, intensity in enumerate(lui.intensities()):
      n = lu.name + '_' + intensity
      n2 = n + '_ref'
      if lu.name == 'timber':
        rasters[n] = SimpleExpr(n, '0')
        rasters[n2] = SimpleExpr(n2, '0')
      else:
        rasters[n] = lui.LUH2(lu.name, intensity)
        rasters[n2] = Raster(n2, ref_path, band + 1)

  ref_path = 'ds/luh2/urban-recal.tif'
  for band, intensity in enumerate(lui.intensities()):
    n = 'urban_' + intensity
    rasters[n] = lui.LUH2('urban', intensity)
    n2 = n + '_ref'
    rasters[n2] = Raster(n2, ref_path, band + 1)

  for lu in ('annual', 'pasture'):
    name = '%s_minimal_and_light' % lu
    rasters[name] = SimpleExpr(name, '%s_minimal + %s_light' % (lu, lu))

  for lu in ('mature_secondary', 'nitrogen', 'rangelands'):
    name = '%s_light_and_intense' % lu
    rasters[name] = SimpleExpr(name, '%s_light + %s_intense' % (lu, lu))

  for intensity in ['light', 'intense']:
    expr = ' + '.join(['%s_%s' % (name, intensity) for
                       name in [lu.name for lu in lus] + ['urban']])
    rasters[intensity] = SimpleExpr(intensity, expr)

  return rasters

def oneKm(year, scenario, hpd_trend):
  rasters = {}
  if scenario == 'version3.3':
    ddir = os.path.join(utils.data_root(), 'version3.3')
    pattern = '{short}.zip!{short}/{short}_MCDlu_(v3_3_Trop)_%d.bil' % year
  else:
    ddir = os.path.join(utils.data_root(), '1km')
    pattern = '{short}_%d.zip!{short}_1km_%d_0ice.bil' % (year, year)
  lus = []
  for name in lu.types():
    short = name[0:3].upper()
    short = 'CRP' if short == 'CRO' else short
    fname = pattern.format(short=short)
    lus.append(Raster(name, 'zip://' + os.path.join(ddir, fname)))
  rasters['plantation_pri'] = SimpleExpr('plantation_pri', '0')
  rasters['plantation_sec'] = SimpleExpr('plantation_sec', '0')

  ## Human population density and UN subregions
  rasters['hpd_ref'] = Raster('hpd_ref',
                              os.path.join(utils.data_root(),
                                           'grump1.0/gluds00ag'))
  rasters['unSub'] = Raster('unSub', 'ds/1km/un_subregions.tif')
  rasters['un_code'] = Raster('un_codes', 'ds/1km/un_codes.tif')
  rasters['hpd'] = hpd.WPP(hpd_trend, year,
                           os.path.join(utils.data_root(),
                                        'wpp',
                                        'WPP2010_DB2_F01_TOTAL_POPULATION_BOTH_SEXES.xls'))

  ## NOTE: Pass max & min of log(HPD) so hi-res rasters can be processed
  ## incrementally.  Recording the max value here for when I create
  ## other functions for other resolutions.
  ## 0.50 =>  20511.541 / 9.92874298232494
  ## 0.25 =>  41335.645 / 10.62948048177454
  ## 1km  => 872073.500 / 13.678628988329825
  rasters['logHPD_rs'] = SimpleExpr('logHPD_rs',
                                    'scale(log(hpd + 1), 0.0, 1.0, 0.0, 14.0)')
  rasters['logDistRd_rs'] = Raster('logDistRd_rs',
                                   'ds/1km/roads-final.tif')

  ## Land use intensity rasters
  for lu_type in lus:
    rasters[lu_type.name] = lu_type
    for band, intensity in enumerate(lui.intensities()):
      n = lu_type.name + '_' + intensity
      if (n in ('urban_light', 'secondary_intense') or
          lu_type == 'plantation_pri'):
        rasters[n] = SimpleExpr(n, '0')
      else:
        rasters[n] = lui.OneKm(lu_type.name, intensity)
  return rasters

def rasterset(lu_src, scenario, year, hpd_trend='medium'):
  if lu_src == 'rcp':
    return rcp(scenario, year, hpd_trend)
  if lu_src == 'luh5':
    return luh5(scenario, year, hpd_trend)
  if lu_src == 'luh2':
    return luh2(scenario, year, hpd_trend)
  if lu_src == '1km':
    return oneKm(year, scenario, hpd_trend)

def predictify(mod):
  # Remove dots from variable names.  Should also remove any characters
  # which cannot appear in a python variable or function name.
  def nodots(root):
    if isinstance(root, str):
      newr = root.replace('.', '_')
      return newr
    return root
  
  syms = mod.hstab
  if not syms:
    return

  if 'UseIntensity' in syms:
    print 'predictify UseIntensity as base'
    f = lambda x: ui.predictify(x, 'UseIntensity')
    mod.equation.transform(f)
    
  for prefix in ('UI', 'UImin2'):
    if prefix in syms:
      if lui.luh5.is_luh5(syms[prefix], prefix):
        print 'predictify %s as luh5' % prefix
        f = lambda x: lui.luh5.predictify(x, prefix)
      elif lui.luh2.is_luh2(syms[prefix], prefix):
        print 'predictify %s as luh2' % prefix
        f = lambda x: lui.luh2.predictify(x, prefix)
      else:
        print 'predictify %s as rcp' % prefix
        f = lambda x: lui.rcp.predictify(x, prefix)
      mod.equation.transform(f)
  if 'LandUse' in syms:
    if lu.luh5.is_luh5(syms['LandUse'], 'LandUse'):
      print 'predictify LandUse as luh5'
      f = lambda x: lu.luh5.predictify(x, 'LandUse')
    elif lui.luh2.is_luh2(syms['LandUse'], 'LandUse'):
      print 'predictify LandUse as luh2'
      f = lambda x: lu.luh2.predictify(x, 'LandUse')
    else:
      print 'predictify LandUse as rcp'
      f = lambda x: lu.rcp.predictify(x, 'LandUse')
    mod.equation.transform(f)
  mod.equation.transform(nodots)
