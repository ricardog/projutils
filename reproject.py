import collections
import numpy as np
import numpy.ma as ma
import rasterio
import rasterio.warp as rwarp

import pdb


def reproject(filename, bidx, resolution, resampling):
    """Returns the resampled Numpy array and the output metadata

    Keyword Arguments:
    filename   -- Input file
    bidx       -- Raster band index (one-based indexing) (default 1)
    resolution -- Multiplier to scale by
    resampling -- Resampling method from rasterio.warp.Resampling enum

    Nota Bene: Nodata value MUST be set or resampling on edges will be
    incorrect!

    """
    with rasterio.open(filename) as src:
        meta = src.meta.copy()
        if not src.crs.is_valid:
            crs = src.crs.from_string(u"epsg:4326")
        else:
            crs = src.crs
        newaff, width, height = rwarp.calculate_default_transform(
            crs, crs, src.width, src.height, *src.bounds, resolution=resolution
        )
        data = ma.empty((src.count, int(height), int(width)), dtype=meta["dtype"])
        newarr = np.empty((int(height), int(width)), dtype=meta["dtype"])
        meta.update(
            {
                "transform": newaff,
                "width": int(width),
                "height": int(height),
                "nodata": src.nodata,
            }
        )

        if bidx is None:
            bidx = range(1, src.count + 1)
        elif not isinstance(bidx, collections.Iterable):
            bidx = [bidx]

        with rasterio.open("/tmp/reproj.tif", "w", **meta) as dst:
            for idx in bidx:
                arr = src.read(idx, masked=True)
                rwarp.reproject(
                    source=arr,
                    destination=newarr,
                    src_transform=src.transform,
                    dst_transform=newaff,
                    src_crs=src.crs,
                    dst_crs=crs,
                    src_nodata=src.nodatavals[idx - 1],
                    dst_nodata=src.nodatavals[idx - 1],
                    resampling=resampling,
                )
                data[idx - 1] = ma.masked_values(newarr, src.nodatavals[idx - 1])
    return meta, data


def reproject2(src, data, resolution, resampling):
    meta = src.meta.copy()
    if not src.crs.is_valid:
        crs = src.crs.from_string(u"epsg:4326")
    else:
        crs = src.crs
    newaff, width, height = rwarp.calculate_default_transform(
        crs, crs, src.width, src.height, *src.bounds, resolution=resolution
    )
    out = ma.empty((src.count, int(height), int(width)), dtype=meta["dtype"])
    newarr = np.empty((int(height), int(width)), dtype=meta["dtype"])
    meta.update(
        {
            "transform": newaff,
            "width": int(width),
            "height": int(height),
            "nodata": src.nodata,
        }
    )

    for idx in range(data.shape[0]):
        rwarp.reproject(
            source=data[idx],
            destination=newarr,
            src_transform=src.transform,
            dst_transform=newaff,
            src_crs=src.crs,
            dst_crs=crs,
            src_nodata=src.nodatavals[idx],
            dst_nodata=src.nodatavals[idx],
            resampling=resampling,
        )
        out[idx] = ma.masked_values(newarr, src.nodatavals[idx])
    return meta, out
