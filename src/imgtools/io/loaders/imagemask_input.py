import pathlib
from dataclasses import dataclass, field
from enum import Enum
from functools import reduce
from typing import Generator, List

import dpath

from imgtools.dicom import Interlacer
from imgtools.dicom.crawl import Crawler, CrawlerSettings
from imgtools.dicom.interlacer import SeriesNode
from imgtools.io.loaders.utils import (
    extract_dicom_tags,
    read_dicom_scan,
)
from imgtools.io.types import ImageMask
from imgtools.modalities import StructureSet
from imgtools.utils import timer

__all__ = ["ImageMaskInput", "ImageMaskModalities"]


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

    roi_pattern: str | None = "(GTV.*|Tumor.*|(oO)(aA)(rR).*)"

    @timer("Initiating ImageMaskInput")
    def __post_init__(self) -> None:
        self.crawler = Crawler.from_settings(self.crawler_settings)

        # TODO:: allow interlacer to take in a df instead of only path
        if self.crawler.db_csv is None or self.crawler.db_json is None:
            msg = "Crawler must have a db attribute to use interlacer."
            raise ValueError(msg)

        self.interlacer = Interlacer(crawl_path=self.crawler.db_csv)

        rawdb = self.crawler._raw_db.copy()

        # based on num of digits in casenum, create lambda padder

        for _, case in self._get_cases():
            scan = case[0]
            if len(rawdb[scan.Series]) == 1:
                s = list(rawdb[scan.Series].values())[0]
            else:
                s = reduce(dpath.merge, rawdb[scan.Series].values())
            mask = case[1]

            m = list(rawdb[mask.Series].values())[0]

            s["filepaths"] = [str(f) for f in s["instances"].values()]
            m["filepaths"] = [str(f) for f in m["instances"].values()]

            assert s["PatientID"] == m["PatientID"], "PatientID mismatch"
            case_id = "__".join(
                [str(s["PatientID"]), s["SeriesInstanceUID"][-5:]]
            )
            print(case_id)

            self._imagemask_db[case_id] = {
                "scan": s,
                "mask": m,
            }

    def _get_cases(
        self, start: int = 1
    ) -> Generator[tuple[int, list[SeriesNode]], None, None]:
        query = self.interlacer._get_valid_query(list(self.modalities))
        all_cases = list(self.interlacer._query(query))
        # First value in each case is a scan
        # positions 1 onward are masks
        # if there is only one mask, it is one element
        # if there are multiple masks, they are in a list
        if len(all_cases) == 0:
            msg = f"No cases found for modalities {self.modalities}."
            raise ValueError(msg)
        counter = start
        for sample in all_cases:
            scan = sample[0]
            masks: List[SeriesNode] = sample[1:]
            match masks:
                case [onemask]:
                    yield counter, [scan, onemask]
                    counter += 1
                case [*many_masks]:
                    for mask in many_masks:
                        yield counter, [scan, mask]
                    counter += 1

    def __len__(self) -> int:
        return len(self._imagemask_db)

    def keys(self) -> List[str]:
        return list(self._imagemask_db.keys())

    def __getitem__(self, key: str | int) -> dict[str, dict]:
        match key:
            case str(caseid) if caseid in self._imagemask_db:
                # return self._load_image_mask(caseid)
                return self._imagemask_db[key]
            case int(caseid) if 0 <= caseid < len(self):
                # return self._load_image_mask(self.keys()[caseid])
                return self._imagemask_db[self.keys()[caseid]]
            case _:
                msg = f"Case {key} not found: {self!r}."
                raise KeyError(msg)

    def __call__(self, key: str | int) -> ImageMask:
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
                    ignore_missing_regex=True,
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

        # dd case_id to metadata for both
        image.metadata["CaseID"] = key
        seg.metadata["CaseID"] = key

        return ImageMask(scan=image, mask=seg)

    def __repr__(self) -> str:
        ncases = len(self)
        modalities = str(self.modalities)
        top = f"ImageMaskInput(cases={ncases}, modalities={modalities})"
        for key in self.keys()[:5]:
            top += f"\n{key}:"
            top += f"\n\tScan({self[key]['scan']['Modality']}): {self[key]['scan']['SeriesInstanceUID']}"
            top += f"\n\tScan({self[key]['mask']['Modality']}): {self[key]['mask']['SeriesInstanceUID']}"
        if ncases > 5:
            top += f"\n...{ncases - 5} more cases."
        return top

    def __iter__(self) -> Generator[ImageMask, None, None]:
        for key in self.keys():
            yield self(key)


if __name__ == "__main__":
    from rich import print

    crawler_settings = CrawlerSettings(
        dicom_dir=pathlib.Path("testdata/Head-Neck-PET-CT"),
        # dicom_dir=pathlib.Path("data"),
        n_jobs=12,
    )
    loader = ImageMaskInput(crawler_settings=crawler_settings)

    first = loader.keys()[0]
    # print(f"{loader[first]=}")
