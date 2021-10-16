import numpy as np
import pandas as pd

from projutils.lui import LUI

def test_lui_base():
    hpd = np.arange(0, 11, 0.1, dtype="float32")
    shape = hpd.shape
    unsub = np.full(shape, 5, dtype="float32")
    crop = np.random.rand(*shape).astype("float32")
    lui = LUI("crop", "intense", "cropland")
    _ = lui.eval({"hpd": hpd,
                  "unSub": unsub,
                  "crop": crop})
    return


def test_lui_minimal():
    hpd = np.arange(0, 11, 0.1, dtype="float32")
    shape = hpd.shape
    unsub = np.full(shape, 5, dtype="float32")
    crop = np.random.rand(*shape).astype("float32")
    #crop = np.linspace(0, 1, shape[0])
    #crop = np.full(shape, 0.1, dtype="float32")
    intense = LUI("crop", "intense", "cropland")
    light = LUI("crop", "light", "cropland")
    minimal = LUI("crop", "minimal", "cropland")

    crop_int = intense.eval({"hpd": hpd,
                             "unSub": unsub,
                             "crop": crop})
    crop_light = light.eval({"hpd": hpd,
                             "unSub": unsub,
                             "crop": crop,
                             "crop_intense": crop_int})
    
    crop_min = minimal.eval({"hpd": hpd,
                             "unSub": unsub,
                             "crop": crop,
                             "crop_intense": crop_int,
                             "crop_light": crop_light})
    assert np.all(crop_min >= -1e-6)
    return


def test_lui_sum():
    hpd = np.arange(0, 11, 0.1, dtype="float32")
    shape = hpd.shape
    unsub = np.full(shape, 5, dtype="float32")
    crop = np.random.rand(*shape).astype("float32")
    intense = LUI("crop", "intense", "cropland")
    light = LUI("crop", "light", "cropland")
    minimal = LUI("crop", "minimal", "cropland")

    crop_int = intense.eval({"hpd": hpd,
                             "unSub": unsub,
                             "crop": crop})
    crop_light = light.eval({"hpd": hpd,
                             "unSub": unsub,
                             "crop": crop,
                             "crop_intense": crop_int})
    crop_min = minimal.eval({"hpd": hpd,
                             "unSub": unsub,
                             "crop": crop,
                             "crop_intense": crop_int,
                             "crop_light": crop_light})
    assert np.allclose(crop, crop_int + crop_light + crop_min)
    return
