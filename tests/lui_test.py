import numpy as np
import pandas as pd

from projutils.lui import LUI

def test_lui_cropland():
    hpd = np.arange(0, 11, 0.1, dtype="float32")
    shape = hpd.shape
    unsub = np.full(shape, 5, dtype="float32")
    crop = np.random.rand(*shape).astype("float32")
    df = pd.DataFrame({"hpd": hpd,
                       "unSub": unsub,
                       "crop": crop})
    lui = LUI("crop", "intense", "cropland")
    _ = lui.eval({"hpd": hpd,
                  "unSub": unsub,
                  "crop": crop})
    return
