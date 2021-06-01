try:
    from osgeo import gdal
except ImportError:
    import gdal
import numpy as np
import numpy.ma as ma
import pandas as pd
import subprocess


def get_props(fname):
    ds = gdal.Open(fname)
    if ds is None:
        raise RuntimeError("failed to read raster %s" % fname)
    proj = ds.GetProjection()
    trans = ds.GetGeoTransform()
    xsize = ds.RasterXSize
    ysize = ds.RasterYSize
    return (xsize, ysize, trans, proj)


def to_array(path, band=1):
    ds = gdal.Open(path)
    if ds is None:
        raise RuntimeError("could not open raster '%s'" % path)
    raster_band = ds.GetRasterBand(int(band))
    data = raster_band.ReadAsArray()
    if raster_band.GetNoDataValue():
        mask = np.isclose(data, raster_band.GetNoDataValue())
    else:
        mask = np.zeros(data.shape)
    return data, mask


def to_pd(path, band=1, xsize=None, ysize=None):            # noqa C901
    if isinstance(path, list) or isinstance(path, tuple):

        def wrapper(args):
            for item in args:
                if len(item) == 3:
                    yield item
                else:
                    yield (item[0], item[1], 1)

        df = pd.DataFrame()
        for name, fname, band in wrapper(path):
            s = to_pd(fname, band, xsize, ysize)
            df[name] = s
            if xsize is None:
                xsize = s.xsize
            if ysize is None:
                ysize = s.ysize
        df.xsize = xsize
        df.ysize = ysize
        return df

    ds = gdal.Open(path)
    if ds is None:
        raise RuntimeError("could not open raster '%s'" % path)
    if xsize:
        assert xsize == ds.RasterXSize
    if ysize:
        assert ysize == ds.RasterYSize
    raster_band = ds.GetRasterBand(int(band))
    s = pd.Series(raster_band.ReadAsArray().reshape(-1))
    if raster_band.GetNoDataValue():
        s[np.isclose(s, raster_band.GetNoDataValue())] = np.nan
    s.xsize = xsize if xsize else ds.RasterXSize
    s.ysize = ysize if ysize else ds.RasterYSize
    return s


def from_array(data, path, xsize, ysize, nodata=-9999, trans="", proj=""):
    geotiff = gdal.GetDriverByName("GTiff")
    dst_ds = geotiff.Create(
        path,
        xsize,
        ysize,
        1,
        gdal.GetDataTypeByName("Float32"),
        ["COMPRESS=lzw", "PREDICTOR=3"],
    )
    if dst_ds is None:
        raise RuntimeError("failed to create output raster '%s'" % path)
    dst_ds.SetProjection(proj)
    dst_ds.SetGeoTransform(trans)
    dst_ds.GetRasterBand(1).SetNoDataValue(nodata)
    dst_ds.GetRasterBand(1).WriteArray(data)
    return dst_ds


def from_pd(df, path, nodata=-9999, trans="", proj=""):
    if isinstance(df, pd.Series):
        arr = df.as_matrix().reshape(df.ysize, df.xsize)
        return from_array(arr, path, df.xsize, df.ysize, nodata, trans, proj)
    if isinstance(df, pd.DataFrame):
        geotiff = gdal.GetDriverByName("GTiff")
        dst_ds = geotiff.Create(
            path,
            df.xsize,
            df.ysize,
            len(df.columns),
            gdal.GetDataTypeByName("Float32"),
            ["COMPRESS=lzw", "PREDICTOR=3"],
        )
        if dst_ds is None:
            raise RuntimeError("failed to create output raster '%s'" % path)
        dst_ds.SetProjection(proj)
        dst_ds.SetGeoTransform(trans)
        for idx, col in enumerate(df.columns):
            arr = df[col].as_matrix().reshape(df.ysize, df.xsize)
            dst_ds.GetRasterBand(idx + 1).SetNoDataValue(nodata)
            dst_ds.GetRasterBand(idx + 1).WriteArray(arr)
    return dst_ds


def to_png(iname, color, oname, band=1):
    """
    Convert a raster to color PNG using the specified palette.  Calls
    gdaldem to do the generation.

    @param iname   file name of input raster
    @param color   file name of color palette
    @param oname   file name of output PNG
    @param band    the raster band to convert o PNG; use -1 for all
    """

    cmd = [
        "gdaldem",
        "color-relief",
        iname,
        color,
        oname,
        "-of",
        "PNG",
        "-b",
        str(band),
    ]
    subprocess.check_output(cmd)


def get_min_max(ds, algo="mincut"):
    low = None
    high = 0.0
    lower = 0.02
    higher = 0.98
    bins = 2048
    bands = ds.RasterCount
    for b in range(1, bands + 1):
        band = ds.GetRasterBand(b)
        stats = band.GetStatistics(False, True)
        histo = band.GetHistogram(
            min=stats[0],
            max=stats[1],
            buckets=bins,
            include_out_of_range=True,
            approx_ok=False,
        )
        count = sum(histo)
        cutoff = (count * lower, count * higher)
        step = (stats[1] - stats[0]) / float(bins)
        if low is None:
            low = stats[1]
        x = stats[0]
        total = 0
        for b in histo:
            total += b
            if total > cutoff[0]:
                low = min(x, low)
            if total > cutoff[1]:
                high = max(x, high)
                break
            x += step
        if high is None:
            high = stats[1]

    return (low, high)


def get_stats(tiffs):
    """
    Returns basic stats for a collection of rasters (min, max, x_size,
    y_size).  Verifies that all rasters have the same dimensions.

    @param tiffs   a list of raster file names to process

    Returns a 5-element list [min, max, x_size, y_size, bands].

    FIXME: change the APi to return a list per input file.
    """

    if tiffs == []:
        return [0, 0, 0, 0, []]
    if isinstance(tiffs, str):
        tiffs = [tiffs]
    low = []
    high = []
    x_size = y_size = None
    all_bands = []
    for tiff in tiffs:
        ds = gdal.Open(tiff)
        if ds is None:
            print("open failed")
            return
        if x_size is None:
            x_size = ds.RasterXSize
            y_size = ds.RasterYSize
        else:
            if x_size != ds.RasterXSize or y_size != ds.RasterYSize:
                print(
                    "raster have mismatched sizes (%d = %d; %d = %d)"
                    % (x_size, ds.RasterXSize, y_size, ds.RasterYSize)
                )
                sys.exit(-1)
        bands = ds.RasterCount
        all_bands.append(bands)
        for b in range(1, bands + 1):
            band = ds.GetRasterBand(b)
            stats = band.GetStatistics(True, True)
            low.append(stats[0])
            high.append(stats[1])
    return (min(low), max(high), x_size, y_size, all_bands)


def mask(name, mask):
    """

    Propagate No Data Values (NODATA) from one raster to another.  Any
    pixel that is NODATA in 'mask' will be set to NODATA in 'name'.  The
    raster is updated in-place.

    @param name filename of raster
    @param mask filename of mask raster
    """

    rmask = gdal.Open(mask)
    nodata = rmask.GetRasterBand(1).GetNoDataValue()
    mask_arr = np.array(rmask.GetRasterBand(1).ReadAsArray())
    nodata_mask = mask_arr == nodata

    raster = gdal.Open(name, gdal.GA_Update)
    band = raster.GetRasterBand(1)
    raster_arr = np.array(band.ReadAsArray())
    out_arr = np.where(nodata_mask == True, nodata, raster_arr) # noqa E712
    band.WriteArray(out_arr)
    band.SetNoDataValue(nodata)


def areg(data, mask, nodata, offset, low, high):
    # FIXME: this function is pointless.
    src_min = np.min(ma.masked_where(mask, data))
    X = np.log(np.where(mask, src_min + offset, data + offset))
    X_min = X.min()
    X_std = (X - X_min) / (X.max() - X_min)
    scaled = X_std * (high - low) + low
    _ = np.where(mask, nodata, scaled)
    return


def regularize(src_fn, dst_fn, src_band=1, offset=1.0, low=0.0, high=1):
    src_ds = gdal.Open(src_fn)
    if src_ds is None:
        raise RuntimeError("Error: could not open raster file '%s'" % src_fn)
    if dst_fn is not None:
        geotiff = gdal.GetDriverByName("GTiff")
        if geotiff is None:
            raise RuntimeError("could not open GeoTiff gdal driver")
        dst_ds = geotiff.Create(
            dst_fn,
            src_ds.RasterXSize,
            src_ds.RasterYSize,
            2,  # Store the unscaled (but log-ed) value in band 2
            gdal.GetDataTypeByName("Float32"),
            ["COMPRESS=lzw", "PREDICTOR=3"],
        )
        if dst_ds is None:
            raise RuntimeError("Error: could not open raster file '%s'" % dst_fn)
        dst_ds.SetProjection(src_ds.GetProjection())
        dst_ds.SetGeoTransform(src_ds.GetGeoTransform())
    src_nodata = src_ds.GetRasterBand(src_band).GetNoDataValue()
    src_data = src_ds.GetRasterBand(src_band).ReadAsArray()
    src_mask = src_data == src_nodata

    # This is a bit awkward.  A masked_array (ma) seemed like the ideal
    # way to compute the log of a raster with NoData values.
    # Unfortunately, ma performs the operation on *all* elements of the
    # array and then does the masking.  So resorting to this goofiness.
    #
    # Need to be careful not to introduce an artificial minimum, i.e. can
    # simply use 1.0 for NoData cells because the minimum in the unmasked
    # portion of the array may be > 1.0.
    src_min = np.min(ma.masked_where(src_mask, src_data))
    X = np.log(np.where(src_mask, src_min + offset, src_data + offset))
    X_min = X.min()
    X_std = (X - X_min) / (X.max() - X_min)
    scaled = X_std * (high - low) + low
    masked = np.where(src_mask, src_nodata, scaled)
    if dst_fn is None:
        return masked
    dst_ds.GetRasterBand(1).WriteArray(masked)
    dst_ds.GetRasterBand(1).SetNoDataValue(src_nodata)
    dst_ds.GetRasterBand(2).WriteArray(np.where(src_mask, src_nodata, X))
    dst_ds.GetRasterBand(2).SetNoDataValue(src_nodata)


if __name__ == "__main__":
    import sys

    ds = gdal.Open(sys.argv[1])
    l, h = get_min_max(ds)
    print("min: %.2f / max: %.2f" % (l, h))
