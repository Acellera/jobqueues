import numpy as np


def ensurelist(tocheck, tomod=None):
    """Convert np.ndarray and scalars to lists.

    Lists and tuples are left as is. If a second argument is given,
    the type check is performed on the first argument, and the second argument is converted.
    """
    if tomod is None:
        tomod = tocheck
    if isinstance(tocheck, np.ndarray):
        return list(tomod)
    if isinstance(tocheck, range):
        return list(tocheck)
    if not isinstance(tocheck, list) and not isinstance(tocheck, tuple):
        return [tomod, ]
    return tomod