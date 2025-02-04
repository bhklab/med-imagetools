from importlib.resources import files

import SimpleITK as sitk

_data_path = files("imgtools.datasets.data")


def data_paths() -> dict[str, str]:
    """Return paths to example dataset files.

    Returns:
        dict[str, str]: A dictionary mapping dataset keys to their file paths.
        Available keys are:
        - "duck": Path to the merged duck with star image
        - "mask": Path to the star mask

    Raises:
        FileNotFoundError: If any of the dataset files are missing
    """
    return {
        "duck": str(_data_path.joinpath("merged_duck_with_star.nii.gz")),
        "mask": str(_data_path.joinpath("star_mask.nii.gz")),
    }


def data_images() -> dict[str, sitk.Image]:
    """Return example dataset images.

    Returns:
        dict[str, sitk.Image]: A dictionary mapping dataset keys to their SimpleITK images.
        Available keys are:
        - "duck": The merged duck with star image
        - "mask": The star mask
    """
    paths = data_paths()
    return {key: sitk.ReadImage(path) for key, path in paths.items()}
