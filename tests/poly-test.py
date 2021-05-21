#!/usr/bin/env python

import gdal

import env
import poly

ds = gdal.Open("/out/hpd/wpp/low.tif")
if ds:
    hpd = ds.GetRasterBand(50).ReadAsArray()
    p2 = poly.poly(hpd, "poly(logHPD.rs, 2)2")
    p1 = poly.poly(hpd, "poly(logHPD.rs, 2)1")
    p0 = poly.poly(hpd, "poly(logHPD.rs, 2)0")
