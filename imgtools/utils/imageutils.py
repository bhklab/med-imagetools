import SimpleITK as sitk
import numpy as np

def physical_points_to_idxs(image, points, continuous=False):
    if continuous:
        transform = image.TransformPhysicalPointToContinuousIndex
    else:
        transform = image.TransformPhysicalPointToIndex
    
    vectorized_transform = np.vectorize(lambda x: np.array(transform(x)), signature='(3)->(3)')
    
    # transform indices to ContourSequence/ContourData-wise
    t_points = []
    for slc in points:
        t_points.append(vectorized_transform(slc)[:,::-1])
    return t_points

def idxs_to_physical_points(image, idxs):
    continuous = any([isinstance(i, float) for i in idxs])

    if continuous:
        transform = image.TransformContinuousIndexToPhysicalPoint
    else:
        transform = image.TransformIndexToPhysicalPoint
    vectorized_transform = np.vectorize(lambda x: np.array(transform(x)), signature='(3)->(3)')
    return vectorized_transform(idxs)

def image_to_array(image):
    origin, direction, spacing = image.GetOrigin(), image.GetDirection(), image.GetSpacing()
    array = sitk.GetArrayFromImage(image)
    return array, origin, direction, spacing

def show_image(image, mask=None, ax=None):
    import matplotlib.pyplot as plt
    if ax is None:
        ax = plt.subplots()

    image_array, *_ = image_to_array(image)

    ax.imshow(image_array, cmap="bone", interpolation="bilinear")

    if mask is not None:
        mask_array, *_ = image_to_array(mask)
        mask_array = np.ma.masked_where(mask_array == 0, mask_array)

        ax.imshow(mask_array, cmap="tab20")

    return ax
