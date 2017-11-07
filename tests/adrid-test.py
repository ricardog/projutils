#!/usr/bin/env python

import gdal
import numpy as np
import os
import pandas as pd
import pprint
import sys

import env
import hpd.wpp
import lu.rcp
import lui.rcp
import rds
import tiff_utils as tu

tf_ab_model = rds.read('../models/ab-tropical-forest.rds')
syms = tf_ab_model.hstab
print("Model symbols:")
pprint.pprint(syms)

# Read in a mask to apply to the output
mask, _ = tu.to_array('../../data/rcp1.1/gicew.1700.txt')
xsize, ysize = mask.shape

# Where to find the RCP raw data files, i.e. gcrop, gthor, etc.
rcp_dir = '/out/lu/rcp/aim/updated_states'
# Where to find baseline land use intensity data
lui_dir = '/out/lui'
# The baseline human population density data
hpd_base = 'gluds00aghd.vrt'
# UN WPP spreadsheet for projecting HPD
wpp = '../../data/wpp/WPP2017_POP_F01_1_TOTAL_POPULATION_BOTH_SEXES.xlsx'
# UN subregions raster
un_sub = '../../data/un_sub'
# UN code raster
un_codes = '../../data/un_codes'

# The year to project to
year = 2030

# Prepare input data; fill all columns in the DataFrame
df = pd.DataFrame()
df['logDistRd.rs'] = tu.to_pd('/out/roads.rs.tif')

# Read human population density and rescale it
df['hpd_base'] = tu.to_pd(hpd_base)
hpd_data = hpd.wpp.project(un_codes, hpd_base, wpp, 'medium', year)
df['hpd'] = hpd_data.reshape(-1)
df['logHPD.rs'] = tu.areg(hpd_data + 1, mask, -9999).reshape(-1)

# Calculate needed land use data
for t in syms['LandUse'].keys():
  df[k + t] = lu.rcp.project(t.lower(), rcp_dir, year).reshape(-1)

# Calculate land use intensity data -- note that it needs to "compute"
# primary
for t in syms['UImin2'].keys():
  df[k + t] = lui.rcp.project(t.lower(), df, un_sub, rcp_dir,
                              lui_dir).reshape(-1)

# Drop rows that have NA, e.g. everything that's water only
df = df.dropna()

# Evaluate model using new data
result = tf_ab_model.eval(df)

# Reshape DataFrame and convert it back to a raster
result2 = result.reindex(range(mask.shape[0] * mask.shape[1]))

# Write the resulting array to a GeoTIFF file
tu.from_pd(result2, '/out/abundance/tf-ab.%d.tif' % year)
