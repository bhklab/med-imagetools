from __future__ import annotations

from dataclasses import dataclass, field

import SimpleITK as sitk

from imgtools.logging import logger

from .helper_types import Coordinate3D, Size3D


# Exception for when the bounding box is outside the image
class BoundingBoxOutsideImageError(Exception):
    """Exception raised when the bounding box is outside the image."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(self.message)


def calculate_image_boundaries(image: sitk.Image) -> RegionBox:
    """
     Calculate the physical coordinate boundaries of a SimpleITK image.

     Parameters
     ----------
     image : sitk.Image
             The input SimpleITK image.

     Returns
     -------
    RegionBox

     Examples
     --------
     >>> calculate_image_boundaries(image)

    """

    size = image.GetSize()
    origin = image.GetOrigin()

    return RegionBox.from_tuple(
        coordmin=(int(origin[0]), int(origin[1]), int(origin[2])),
        coordmax=(
            int(origin[0] + size[0]),
            int(origin[1] + size[1]),
            int(origin[2] + size[2]),
        ),
    )


@dataclass
class RegionBox:
    """Represents a box in 3D space.

    Attributes
    ----------
    min : Coordinate3D
        The minimum coordinate of the box.
    max : Coordinate3D
        The maximum coordinate of the box.

    size : Size3D
        The size of the box, calculated from the min and max coordinates.
    """

    min: Coordinate3D
    max: Coordinate3D
    size: Size3D = field(init=False)

    @classmethod
    def from_tuple(
        cls, coordmin: tuple[int, int, int], coordmax: tuple[int, int, int]
    ) -> RegionBox:
        """Creates a RegionBox from a tuple of min and max coordinates."""
        return cls(Coordinate3D(*coordmin), Coordinate3D(*coordmax))

    @classmethod
    def from_mask_centroid(cls, mask: sitk.Image, label: int = 1) -> RegionBox:
        """Creates a RegionBox from the centroid of a mask image.

        Parameters
        ----------
        mask : sitk.Image
            The input mask image.

        Returns
        -------
        BoundingBox
            The bounding box coordinates as a BoundingBox object.
        """
        mask_uint = sitk.Cast(mask, sitk.sitkUInt8)
        stats = sitk.LabelShapeStatisticsImageFilter()
        stats.Execute(mask_uint)

        centroid = stats.GetCentroid(label)
        centroid_idx = mask.TransformPhysicalPointToIndex(centroid)

        return RegionBox(
            Coordinate3D(*centroid_idx), Coordinate3D(*centroid_idx)
        )

    @classmethod
    def from_mask(cls, mask: sitk.Image, label: int = 1) -> RegionBox:
        """Creates a RegionBox from the bounding box of a mask image.

        Parameters
        ----------
        mask : sitk.Image
            The input mask image.
        min_dim_size : int
            Minimum size of bounding box along each dimension. Default is 4.

        Returns
        -------
        BoundingBox
            The bounding box coordinates as a BoundingBox object.
        """

        mask_uint = sitk.Cast(mask, sitk.sitkUInt8)
        stats = sitk.LabelShapeStatisticsImageFilter()
        stats.Execute(mask_uint)
        xstart, ystart, zstart, xsize, ysize, zsize = stats.GetBoundingBox(
            label
        )

        return RegionBox(
            Coordinate3D(xstart, ystart, zstart),
            Coordinate3D(xstart + xsize, ystart + ysize, zstart + zsize),
        )

    def __post_init__(self) -> None:
        if (
            self.min.x > self.max.x
            or self.min.y > self.max.y
            or self.min.z > self.max.z
        ):
            msg = "The minimum coordinate must be less than the maximum coordinate."
            msg += f" Got: min={self.min}, max={self.max}"
            raise ValueError(msg)

        self.size = Size3D(
            self.max.x - self.min.x,
            self.max.y - self.min.y,
            self.max.z - self.min.z,
        )

    def __repr__(self) -> str:
        """prints out like this:

        RegionBox(
            min=Coordinate3D(x=223, y=229, z=57),
            max=Coordinate3D(x=303, y=299, z=87)
            size=(80, 70, 30)
        )
        """
        return (
            f"{self.__class__.__name__}(\n"
            f"\tmin={self.min},\n"
            f"\tmax={self.max}\n"
            f"\tsize={self.size}\n"
            f")"
        )

    def pad(self, padding: int) -> RegionBox:
        """Expand the bounding box by a specified padding value in all directions.

        Parameters
        ----------
        padding : int
            The padding value to expand the bounding box.

        Returns
        -------
        RegionBox
            The expanded bounding box.
        """
        if padding == 0:
            return self

        padded_min = Coordinate3D(
            self.min.x - padding,
            self.min.y - padding,
            self.min.z - padding,
        )
        padded_max = Coordinate3D(
            self.max.x + padding,
            self.max.y + padding,
            self.max.z + padding,
        )
        return RegionBox(min=padded_min, max=padded_max)

    def expand_to_cube(self, desired_size: int | None = None) -> RegionBox:
        """Convert the bounding box to a cube by making the size equal along all dimensions.

        This is done by finding which dimension is the largest,
        and then pad the other dimensions to make them equal to the desired size.

        Parameters
        ----------
        desired_size : int | None
            The desired size of the cube. If None, the maximum dimension size is used

        Returns
        -------
        RegionBox
            The bounding box converted to a cube.

        Raises
        ------
        ValueError
            If the desired size is smaller than the current maximum dimension size.
        """
        max_size = max(self.size)

        if not desired_size:
            return self.minimum_dimension_size(max_size)

        if desired_size < max_size:
            msg = (
                f"Desired size {desired_size} is smaller than"
                f" the current maximum dimension size {max_size}."
            )
            raise ValueError(msg)

        return self.minimum_dimension_size(desired_size)

    def minimum_dimension_size(self, size: int = 5) -> RegionBox:
        """Ensure that the bounding box has a minimum size along each dimension.

        Parameters
        ----------
        size : int
            The minimum size of the bounding box along each dimension.

        Returns
        -------
        RegionBox
            The bounding box with a minimum size along each dimension.

        Notes
        -----
        Validation is done to ensure that any min coordinates that are negative are set to 0,
        and the difference is added to the maximum coordinates
        """
        extra_x = max(0, size - self.size.width) // 2
        extra_y = max(0, size - self.size.height) // 2
        extra_z = max(0, size - self.size.depth) // 2

        min_coord = self.min - (extra_x, extra_y, extra_z)
        max_coord = self.max + (extra_x, extra_y, extra_z)

        self._adjust_negatived_coordinates(min_coord, max_coord)

        return RegionBox(min=min_coord, max=max_coord)

    def _adjust_negatived_coordinates(
        self, min_coord: Coordinate3D, max_coord: Coordinate3D
    ) -> None:
        """Adjust the coordinates to ensure that the min values are not negative."""
        # if any of the min values are negative, set them to 0,
        # and add the difference to the max values
        for axis in ["x", "y", "z"]:
            min_value = getattr(min_coord, axis)
            if min_value < 0:
                diff = abs(min_value)
                setattr(min_coord, axis, 0)
                setattr(max_coord, axis, getattr(max_coord, axis) + diff)

    def crop_image(self, image: sitk.Image) -> sitk.Image:
        """Crop an image to the coordinates defined by the box.

        Parameters
        ----------
        image : sitk.Image
            The image to crop.

        Returns
        -------
        sitk.Image
            The cropped image.
        """
        try:
            cropped_image = sitk.RegionOfInterest(image, self.size, self.min)
        except RuntimeError as e:
            msg = (
                f"The box {self} is outside"
                f" the image size {calculate_image_boundaries(image)} "
            )
            # this is probably due to the box being outside the image
            # try to crop the image to the largest possible region
            # we could handle this in the future, for now let it raise the error
            # and make user try again with an adjusted box
            raise BoundingBoxOutsideImageError(msg) from e
        else:
            return cropped_image


if __name__ == "__main__":
    from rich import print  # noqa

    basicbox = RegionBox(Coordinate3D(5, 5, 5), Coordinate3D(10, 10, 10))

    print(basicbox)

    tupleinitbox = RegionBox.from_tuple((5, 5, 5), (10, 10, 10))

    print(tupleinitbox)

    # create a 3D image
    image = sitk.Image(100, 100, 100, sitk.sitkInt16)

    cropped_image = basicbox.crop_image(image)

    print(f"{cropped_image.GetSize()=}")

    non_uniform_box = RegionBox(
        Coordinate3D(5, 5, 5), Coordinate3D(21, 23, 29)
    )

    print(f"{non_uniform_box=}")

    padded_box = non_uniform_box.pad(5)

    print(f"{padded_box=}")

    cube_box = non_uniform_box.expand_to_cube()

    print(f"{cube_box=}")

    min_size_box = non_uniform_box.minimum_dimension_size(30)
    print(f"{min_size_box=}")

    print(f"{non_uniform_box.expand_to_cube().minimum_dimension_size(50)=}")

    try:
        box_outsided_image = RegionBox(
            Coordinate3D(0, 0, 0), Coordinate3D(200, 200, 200)
        )

        cropped_image = box_outsided_image.crop_image(image)

        print(f"{cropped_image.GetSize()=}")
    except BoundingBoxOutsideImageError as e:
        print("ERROR")
        print(e)

    ########################################
    # from masks
    ########################################

    ct_image = sitk.ReadImage(
        "/home/bioinf/bhklab/radiomics/readii-negative-controls/rawdata/HEAD-NECK-RADIOMICS-HN1/images/niftis/SubjectID-100_HN1339/CT_82918_original.nii.gz"
    )
    rt_image = sitk.ReadImage(
        "/home/bioinf/bhklab/radiomics/readii-negative-controls/rawdata/HEAD-NECK-RADIOMICS-HN1/images/niftis/SubjectID-100_HN1339/RTSTRUCT_11267_GTV.nii.gz"
    )

    print(f"{RegionBox.from_mask(rt_image)=}")

    print(f"{RegionBox.from_mask_centroid(rt_image)=}")

    print(f"{RegionBox.from_mask_centroid(rt_image).expand_to_cube(50)=}")

    print(
        f"{RegionBox.from_mask_centroid(rt_image).expand_to_cube(50).minimum_dimension_size(30)=}"
    )

    ## assign
    centroid_region = RegionBox.from_mask_centroid(rt_image).expand_to_cube(
        100
    )
    bbox_region = RegionBox.from_mask(rt_image).expand_to_cube(100)

    cropped_centroid_image = centroid_region.crop_image(ct_image)
    cropped_bbox_image = bbox_region.crop_image(ct_image)

    for name, img in zip(
        ("cropped_centroid_image", "cropped_bbox_image"),
        (cropped_centroid_image, cropped_bbox_image),
        strict=True,
    ):
        print("*" * 20)
        print(f"{name}")
        print(f"{img.GetSize()=}")
        print(f"{img.GetOrigin()=}")
        print(f"{img.GetSpacing()=}")
        print(f"{img.GetDirection()=}")
