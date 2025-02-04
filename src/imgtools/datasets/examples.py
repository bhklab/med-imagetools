from importlib.resources import files

_data_path = files("imgtools.datasets.data")


def data_paths() -> dict[str, str]:
    return {
        "duck": str(_data_path.joinpath("merged_duck_with_star.nii.gz")),
        "mask": str(_data_path.joinpath("star_mask.nii.gz")),
    }
