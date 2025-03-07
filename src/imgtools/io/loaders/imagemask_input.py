import pathlib
from dataclasses import dataclass, field
from enum import Enum
from functools import reduce
from typing import Any, Callable, Generator, List, NamedTuple, Optional

import dpath
import SimpleITK as sitk

from imgtools.dicom.crawl import Crawler, CrawlerSettings
from imgtools.io.loaders.utils import (
    read_dicom_auto,
    read_dicom_scan,
    extract_dicom_tags,
    read_dicom_rtstruct,
)
from imgtools.logging import logger
from imgtools.modalities import Scan, Segmentation, StructureSet
from imgtools.modalities.interlacer import Interlacer
from imgtools.utils import timer

# from imgtools.modules import Scan, Segmentation, StructureSet
# from imgtools.modules.datagraph import DataGraph
# from imgtools.ops.base_classes import BaseInput
# from imgtools.utils.timer import timer

LoaderFunction = Callable[..., sitk.Image | StructureSet | Segmentation]


class ImageMask(NamedTuple):
    """
    NamedTuple for storing image-mask pairs.

    Parameters
    ----------
    scan : Scan
        The scan image.
    mask : Segmentation
        The mask image.
    """

    scan: Scan
    mask: Segmentation


class ImageMaskModalities(Enum):
    CT_RTSTRUCT = ("CT", "RTSTRUCT")
    CT_SEG = ("CT", "SEG")
    MR_RTSTRUCT = ("MR", "RTSTRUCT")
    MR_SEG = ("MR", "SEG")

    def __str__(self) -> str:
        return f"<{self.value[0]},{self.value[1]}>"

    def __iter__(self) -> Generator:
        yield from self.value


@dataclass
class ImageMaskInput:
    crawler_settings: CrawlerSettings
    crawler: Crawler = field(init=False, repr=False)

    interlacer: Interlacer = field(init=False, repr=False)

    _imagemask_db: dict[str, dict[str, dict]] = field(default_factory=dict)
    modalities: ImageMaskModalities = ImageMaskModalities.CT_RTSTRUCT

    roi_pattern: str | None = "GTV.*"

    @timer("Initiating ImageMaskInput")
    def __post_init__(self) -> None:
        self.crawler = Crawler.from_settings(self.crawler_settings)

        # TODO:: allow interlacer to take in a df instead of only path
        if self.crawler.db_csv is None or self.crawler.db_json is None:
            msg = "Crawler must have a db attribute to use interlacer."
            raise ValueError(msg)

        self.interlacer = Interlacer(
            crawl_path=self.crawler.db_csv, query_branches=True
        )

        rawdb = self.crawler._raw_db.copy()
        allcases = list(self.interlacer._query(set(self.modalities)))

        # based on num of digits in casenum, create lambda padder
        _padder = lambda x: str(x).zfill(len(str(len(allcases))))

        for casenum, (scan, mask) in enumerate(allcases, start=1):
            if len(rawdb[scan.Series]) == 1:
                s = list(rawdb[scan.Series].values())[0]
            else:
                s = reduce(dpath.merge, rawdb[scan.Series].values())

            m = list(rawdb[mask.Series].values())[0]

            s["filepaths"] = [str(f) for f in s["instances"].values()]
            m["filepaths"] = [str(f) for f in m["instances"].values()]

            assert s["PatientID"] == m["PatientID"], "PatientID mismatch"
            case_id = f"{_padder(casenum)}__{s['PatientID']}"

            self._imagemask_db[case_id] = {
                "scan": s,
                "mask": m,
            }

    def __len__(self) -> int:
        return len(self._imagemask_db)

    def keys(self) -> List[str]:
        return list(self._imagemask_db.keys())

    def __getitem__(self, key: str | int) -> ImageMask:
        match key:
            case str(caseid) if caseid in self._imagemask_db:
                return self._load_image_mask(caseid)
            case int(caseid) if 0 <= caseid < len(self):
                return self._load_image_mask(self.keys()[caseid])
            case _:
                msg = f"Case {key} not found: {self!r}."
                raise KeyError(msg)

    def _load_image_mask(self, key: str) -> ImageMask:
        sample = self._imagemask_db[key]
        scan = sample["scan"]
        mask = sample["mask"]

        # because folder is relative to dicom_dir
        root = self.crawler.dicom_dir.parent

        scan_folder = scan["folder"]
        mask_folder = mask["folder"]

        scan_paths = [
            str((root / scan_folder / f).as_posix()) for f in scan["filepaths"]
        ]
        assert len(scan_paths) > 0

        mask_paths = [root / mask_folder / f for f in mask["filepaths"]]

        assert len(mask_paths) == 1, (
            f"Expected only one mask file, but found {len(mask_paths)} "
            f"for case {key}."
        )

        image = read_dicom_scan(
            root / scan_folder,
            scan["SeriesInstanceUID"],
            file_names=scan_paths,
        )

        image.metadata.update(extract_dicom_tags(scan_paths[0]))

        match mask["Modality"]:
            case "RTSTRUCT":
                rtstruct = StructureSet.from_dicom(
                    mask_paths[0],
                    suppress_warnings=True,
                    roi_name_pattern=self.roi_pattern,
                )
                seg = rtstruct.to_segmentation(
                    reference_image=image,
                    roi_names=self.roi_pattern,
                    continuous=False,
                )
                if not seg:
                    msg = f"No ROIs found for case {key}."
                    raise ValueError(msg)
                seg.metadata.update(extract_dicom_tags(mask_paths[0]))
            case "SEG":
                # TODO: properly implement SEG.from_dicom
                raise NotImplementedError("SEG not implemented yet.")
            case _:
                msg = f"Modality {mask['Modality']} not supported."
                raise ValueError(msg)

        return ImageMask(scan=image, mask=seg)

    def __repr__(self) -> str:
        ncases = len(self)
        modalities = str(self.modalities)
        return f"ImageMaskInput(cases={ncases}, modalities={modalities})"

    def __iter__(self) -> Generator[ImageMask, None, None]:
        for key in self.keys():
            yield self[key]


if __name__ == "__main__":
    crawler_settings = CrawlerSettings(
        dicom_dir=pathlib.Path("testdata/Head-Neck-PET-CT"),
        n_jobs=12,
    )
    loader = ImageMaskInput(crawler_settings=crawler_settings)

    first = loader.keys()[0]
    # print(f"{first=} : {loader[first]=}")
