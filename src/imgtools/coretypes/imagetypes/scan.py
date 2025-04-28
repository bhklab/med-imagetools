from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from imgtools.coretypes import MedImage
from imgtools.io.readers import read_dicom_series
from imgtools.loggers import logger

if TYPE_CHECKING:
    import SimpleITK as sitk

__all__ = ["Scan"]


def read_dicom_scan(
    path: str,
    series_id: str | None = None,
    recursive: bool = False,
    file_names: list[str] | None = None,
    **kwargs: Any,  # noqa
) -> Scan:
    """Read a DICOM scan from a directory.

    Parameters
    ----------
    path : str
        Path to the directory containing the DICOM files.
    series_id : str | None, optional
        Series ID to read, by default None
    recursive : bool, optional
        Whether to read the files recursively, by default False
    file_names : list[str] | None, optional
        List of file names to read, by default None
    **kwargs : Any
        Unused keyword arguments.
    Returns
    -------
    Scan
        The read scan.
    """
    return Scan.from_dicom(
        path,
        series_id=series_id,
        recursive=recursive,
        file_names=file_names,
        **kwargs,
    )


class Scan(MedImage):
    metadata: Dict[str, Any]

    def __init__(self, image: sitk.Image, metadata: Dict[str, Any]) -> None:
        super().__init__(image)
        self.metadata = metadata
        self._fix_direction()

    def _fix_direction(self) -> None:
        """Validation of the image.
        sitk 2.4.0 now considers the `SpacingBetweenSlices` when determining
        the direction of the image. Sometimes, this is negative, which
        causes the z-axis to be flipped:
        - Direction([1.00,0.00,0.00], [0.00,1.00,0.00], [0.00,0.00,-1.00])

        So we need to check if the image is flipped and correct it.
        See https://github.com/SimpleITK/SimpleITK/issues/2214

        Note: if this is undesired behaviorm, we can have a config option to
        disable this manual fixing
        """

        slice_spacing = float(self.metadata.get("SpacingBetweenSlices") or 0)
        if (not slice_spacing) or (slice_spacing >= 0):
            return

        # just because metadata says that the spacing is negative, still
        # check if the image is flipped
        # in case  Scan was created from another (correct) Scan's transform
        if self.direction.to_matrix()[2][2] > 0:
            return

        warnmsg = (
            f"Scan has negative SpacingBetweenSlices: {slice_spacing}. "
            "Manually correcting the direction."
        )
        logger.debug(
            warnmsg,
            spacing=self.spacing,
            direction=self.direction,
        )

        self.SetDirection(self.direction.flip_axis(2))
        logger.debug(
            "Scan direction corrected.",
            spacing=self.spacing,
            direction=self.direction,
        )

    @classmethod
    def from_dicom(
        cls,
        path: str,
        series_id: str | None = None,
        recursive: bool = False,
        file_names: list[str] | None = None,
        **kwargs: Any,  # noqa
    ) -> Scan:
        """Read a DICOM scan from a directory.

        Parameters
        ----------
        path : str
            Path to the directory containing the DICOM files.
        series_id : str | None, optional
            Series ID to read, by default None
        recursive : bool, optional
            Whether to read the files recursively, by default False
        file_names : list[str] | None, optional
            List of file names to read, by default None
        **kwargs : Any
            Unused keyword arguments.
        Returns
        -------
        Scan
            The read scan.
        """
        image, metadata = read_dicom_series(
            path,
            series_id=series_id,
            recursive=recursive,
            file_names=file_names,
            **kwargs,
        )

        return cls(image, metadata)

    def __repr__(self) -> str:  # type: ignore
        # convert metadata and img_stats to string
        # with angulated brackets
        retr_str = "Scan<"
        for k, v in self.metadata.items():
            retr_str += f"\n\t{k}={v}" if v else ""
        retr_str += "\n>"
        return retr_str

    def __rich_repr__(self):  # type: ignore[no-untyped-def] # noqa: ANN204
        yield "modality", self.metadata.get("Modality", "Unknown")
        yield from super().__rich_repr__()


if __name__ == "__main__":  # pragma: no cover
    from rich import print  # noqa: A004

    directory = "data/4D-Lung/113_HM10395/CT_Series-00173972"
    scan = read_dicom_scan(directory)
    print(f"{scan!r}")  # noqa
    print(scan.fingerprint)
