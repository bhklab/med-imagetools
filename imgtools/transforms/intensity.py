import SimpleITK as sitk


def clip(image, lower, upper):
    pass


def window(image, window, level):
    pass


def mean(image, mask=None, labels=None):
    if mask is not None:
        pass
    pass

def var(image, mask=None, labels=None):
    if mask is not None:
        pass
    pass

def standard_scale(image, dataset_mean=0., dataset_var=1.):
    return (image - dataset_mean) / dataset_var

