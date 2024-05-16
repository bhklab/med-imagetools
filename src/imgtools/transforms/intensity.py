def clip(image, lower, upper):
    return NotImplementedError


def window(image, window, level):
    return NotImplementedError


def mean(image, mask=None, labels=None):
    if mask is not None:
        pass
    return NotImplementedError


def var(image, mask=None, labels=None):
    if mask is not None:
        pass
    return NotImplementedError


def standard_scale(image, dataset_mean=0., dataset_var=1.):
    return (image - dataset_mean) / dataset_var
