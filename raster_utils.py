#!/usr/bin/env python3

import numpy as np
import numpy.ma as ma
import rasterio


def clip(infile, outfile, a_min=None, a_max=None, mask=False):
    if a_min is None and a_max is None:
        print("Please specify min, max, or both")
        return

    with rasterio.open(infile) as src:
        with rasterio.open(outfile, "w", **src.meta) as dst:
            for _, window in src.block_windows(1):
                data = src.read(masked=True, window=window)
                if mask:
                    clipped = data
                    if a_max:
                        clipped = ma.masked_greater(clipped, a_max)
                    if a_min:
                        clipped = ma.masked_less(clipped, a_min)
                else:
                    clipped = np.clip(data, a_min, a_max)
                dst.write(clipped.filled(src.nodata), window=window)
