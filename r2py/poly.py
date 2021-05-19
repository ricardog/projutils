from joblib import memory
from numba import jit, vectorize
import numpy as np
import pandas as pd
import re
import tempfile

from .tree import Node

RE = re.compile("poly\(([^,]+),\s*(\d+)\)$")
TERM_RE = re.compile("(" + RE.pattern.replace("$", "") + ")(\d+)")

# Cache on disk (but available via mmap) the results of the orthogonal
# polynomials.
# memcache = memory.Memory(cachedir=tempfile.mkdtemp(prefix='poly-cache'),
#                         verbose=1, mmap_mode='r')


def poly_parse(node):
    m = re.match(TERM_RE, node)
    if m is None:
        raise ValueError("not a poly term '%s'" % node)
    term = m.group(1)
    var = m.group(2)
    power = int(m.group(3))
    degree = int(m.group(4))
    assert int(degree) <= int(power), "expected degree <= power"
    return var, power, degree


def poly(x, what, norm2=None, alpha=None):
    if isinstance(what, str):
        _, power, degree = poly_parse(what)
    elif isinstance(what, list):
        assert len(what) == 2, "unexpected number of arguments to poly()"
        power, degree = what
    else:
        raise ValueError("unexpected type '%s'" % str(type(what)))
    shape = x.shape
    if norm2 and alpha:
        Z = ortho_poly_predict(x.reshape(-1), np.array(norm2), np.asarray(alpha), power)
    else:
        Z, _, _ = ortho_poly_fit(x.reshape(-1), power)
    ret = Z[:, degree].reshape(shape)
    return ret


# @memcache.cache
def ortho_poly_fit(x, degree=1):
    n = degree + 1
    x = np.asarray(x).flatten()
    if degree >= len(np.unique(x)):
        stop("'degree' must be less than number of unique points")
    xbar = np.mean(x)
    x = x - xbar
    X = np.fliplr(np.vander(x, n))
    q, r = np.linalg.qr(X)

    z = np.diag(np.diag(r))
    raw = np.dot(q, z)

    norm2 = np.sum(raw ** 2, axis=0)
    alpha = (np.sum((raw ** 2) * np.reshape(x, (-1, 1)), axis=0) / norm2 + xbar)[
        :degree
    ]
    Z = raw / np.sqrt(norm2)
    return Z, norm2, alpha


def ortho_poly_predict(x, norm2, alpha, degree=1):
    x = np.asarray(x).flatten()
    n = degree + 1
    Z = np.empty((len(x), n), dtype=x.dtype)
    Z[:, 0] = 1
    if degree > 0:
        Z[:, 1] = x - alpha[0]
    if degree > 1:
        for i in np.arange(1, degree):
            Z[:, i + 1] = (x - alpha[i]) * Z[:, i] - (norm2[i] / norm2[i - 1]) * Z[
                :, i - 1
            ]
    Z /= np.sqrt(norm2)
    return Z


@vectorize(nopython=True, cache=True)
def inv_logit(p):
    return np.exp(p) / (1 + np.exp(p))


def scale(x, low, high, x_min=None, x_max=None):
    xx = x.values if isinstance(x, pd.Series) else x
    if x_min is None:
        x_min = x.min()
    if x_max is None:
        x_max = x.max()
    return __scale(
        xx, np.float32(low), np.float32(high), np.float32(x_min), np.float32(x_max)
    )


@jit(nopython=True, cache=True)
def __scale(x, low, high, x_min=None, x_max=None):
    x_std = (x - x_min) / (x_max - x_min)
    scaled = x_std * (high - low) + low
    return scaled
