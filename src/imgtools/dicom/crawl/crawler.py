from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

import dpath
import pandas as pd
from tqdm import tqdm

from imgtools.dicom.crawl import parse_dicom_dir
from imgtools.logging import logger, tqdm_logging_redirect

__all__ = ["CrawlerSettings", "Crawler"]


@dataclass
class CrawlerSettings:
    """Settings for the DICOM crawler."""

    dicom_dir: Path
    n_jobs: int
    dcm_extension: str = "dcm"
    force: bool = False
    db_json: Path | None = None
    db_csv: Path | None = None
    dataset_name: str | None = None

    def __str__(self) -> str:
        """Return a string representation of the settings."""
        return (
            f"CrawlerSettings(\n"
            f"  dicom_dir: {self.dicom_dir}\n"
            f"  n_jobs: {self.n_jobs}\n"
            f"  dcm_extension: {self.dcm_extension}\n"
            f"  force: {self.force}\n"
            f"  db_json: {self.db_json}\n"
            f"  db_csv: {self.db_csv}\n"
            f"  dataset_name: {self.dataset_name}\n"
            ")"
        )


@dataclass
class Crawler:
    dicom_dir: Path
    n_jobs: int
    dcm_extension: str = "dcm"
    force: bool = False
    db_json: Path | None = None
    db_csv: Path | None = None
    dataset_name: str | None = None

    # Internal
    _raw_db: dict = field(init=False, repr=False)
    _sop_map: dict = field(init=False, repr=False)
    _metadata_gen: Generator[dict, None, None] = field(init=False, repr=False)

    # aggregated database to create a pandas DataFrame after remapping
    # unused if reading from an existing crawldb (i.e `force=False`)
    _agg_db: list[dict] = field(init=False, repr=False, default_factory=list)

    @classmethod
    def from_settings(cls, settings: CrawlerSettings) -> Crawler:
        """Create a Crawler instance from a CrawlerSettings object."""
        return cls(
            dicom_dir=settings.dicom_dir,
            n_jobs=settings.n_jobs,
            dcm_extension=settings.dcm_extension,
            force=settings.force,
            db_json=settings.db_json,
            db_csv=settings.db_csv,
            dataset_name=settings.dataset_name,
        )

    def __post_init__(self) -> None:
        if not self.dicom_dir.is_dir():
            msg = f"Directory not found: {self.dicom_dir}"
            raise FileNotFoundError(msg)

        # default dataset name is the name of the directory
        self.dataset_name = self.dataset_name or self.dicom_dir.name

        # default path is
        # {dicom_dir.parent}/.imgtools/{dataset_name}/crawldb.json
        if not self.db_json:
            self.db_json = (
                self.dicom_dir.parent
                / ".imgtools"
                / self.dataset_name
                / "crawldb.json"
            )
        raw_output_path = self.db_json.with_name("raw_crawldb.json")
        if not self.db_csv:
            self.db_csv = self.db_json.with_suffix(".csv")

        if self.db_json.exists() and not self.force:
            logger.warning(
                f"Found existing crawldb at {self.db_json}."
                " Use `force=True` to overwrite."
            )
            with self.db_json.open("r") as f:
                import json

                self._raw_db = json.load(f)

        else:
            # run the crawl
            self.crawl(raw_output_path)

            # initialize metadata generator
            self._metadata_gen = self._metadata_generator()

            # remap references
            logger.info("Remapping references in the crawldb...")
            self.remap_refs()

            # save the updated crawl_db
            with self.db_json.open("w") as f:
                import json

                json.dump(self._raw_db, f, indent=2)
            logger.info(f"Remapped crawldb saved to {self.db_json}")

        if not self.db_csv.exists() or self.force:
            # convert to pandas DataFrame
            df = self.to_df().sort_values(
                ["PatientID", "StudyInstanceUID", "Modality"]
            )
            df.to_csv(self.db_csv, index=False)
            logger.info(
                f"Converted crawldb to DataFrame and saved to {self.db_csv}"
            )

    def crawl(self, raw_output_path: Path) -> None:
        """Crawl the DICOM directory and build the crawldb.

        Sets the internal `_raw_db` and `_sop_map` attributes.
        """

        logger.info(
            "Crawling DICOM directory...",
            dir=self.dicom_dir,
            extension=self.dcm_extension,
            n_jobs=self.n_jobs,
            force=self.force,
        )
        with tqdm_logging_redirect():
            db_path, crawl_db, sopmap_path, sop_map = parse_dicom_dir(
                dicom_dir=self.dicom_dir,
                raw_output_path=raw_output_path,
                extension=self.dcm_extension,
                n_jobs=self.n_jobs,
                force=self.force,
            )
        self._raw_db = crawl_db
        self._sop_map = sop_map
        logger.info(f"Found {len(crawl_db)} Series in {db_path}")
        logger.info(f"Found {len(sop_map)} Instances in {sopmap_path}")

    ########################################################
    # Utility methods
    ########################################################
    def __getitem__(self, seriesuid: str) -> dict:
        return self._raw_db[seriesuid]

    @property
    def series_uids(self) -> list[str]:
        return list(self._raw_db.keys())

    def _metadata_generator(self) -> Generator[dict, None, None]:
        """Helper generator to flatten the nested structure of the crawldb."""
        for seriesuid in self.series_uids:
            yield from self._raw_db[seriesuid].values()

        # reset the generator
        self._metadata_gen = self._metadata_generator()

    @property
    def metadata_dictionaries(self) -> Generator[dict, None, None]:
        """Return the metadata dictionaries for all series.

        Flattens the nested structure of the crawldb for easier iteration.
        Each yielded dictionary contains DICOM metadata for a specific subseries.

        Yields:
            dict: DICOM metadata dictionary for a subseries

        Example:
            >>> for metadata in crawler.metadata_dictionaries:
            ...     print(metadata.get("SeriesDescription"))
        """
        return self._metadata_gen

    def lookup_sop(self, sop_instance_uid: str) -> str | None:
        """Get the SeriesInstanceUID corresponding to a SOPInstanceUID."""
        return self._sop_map.get(sop_instance_uid)

    def series_to_modality(self, seriesuid: str) -> str:
        """Return the modality of the series with the given SeriesInstanceUID."""
        return list(self._raw_db[seriesuid].values())[0].get("Modality")

    ########################################################
    # Public methods
    ########################################################
    def remap_refs(self) -> None:  # noqa: PLR0912
        """Remap references in the database.

        The goal is to get the `ReferencedSeriesUID` for as many series as possible.
        Whereas some series directly reference the `SeriesInstanceUID` of another series,
        others reference one or more `SOPInstanceUID` of instances in another series.
        This method tries to resolve the latter case by mapping the `SOPInstanceUID` to the
        `SeriesInstanceUID` of the series it belongs to.

        Side effects:
        1) as we iterate over the metadata dictionaries, we add the
            `ReferencedSeriesUID` field to the metadata dictionaries in the crawldb.
        2) we also append the metadata dictionaries to the `_agg_db` list
            for easy conversion to a pandas DataFrame later

        Notes
        -----
        This mutates the metadata dictionaries in the crawldb in place.
        i.e the `ReferencedSeriesUID` field is added to metadata dicts
            in `self._crawl_db` database.
        """
        frame_mapping = defaultdict(set)

        # create a frame of reference map
        for seriesuid, subseries in dpath.search(
            self._raw_db, "*/**/FrameOfReferenceUID"
        ).items():
            for meta in subseries.values():
                if frame := meta.get("FrameOfReferenceUID"):
                    frame_mapping[frame].add(seriesuid)

        for meta in tqdm(
            list(self.metadata_dictionaries),
            desc="Remapping references",
            leave=False,
        ):
            if (ref := meta.get("ReferencedSeriesUID")) and ref in self.series_uids:  # fmt: skip
                # early exit if the reference is already a SeriesInstanceUID
                self._agg_db.append(
                    meta
                )  # add to the aggregated db for easy conversion to df
                continue
            else:
                meta["ReferencedSeriesUID"] = None

            # but for now....
            match meta["Modality"]:
                case "RTSTRUCT" | "RTDOSE" | "RTPLAN":
                    # sop_ref is a single string for RTSTRUCT, RTDOSE, RTPLAN
                    if not (sop_ref := meta.get("ReferencedSOPUIDs")):
                        continue
                    if seriesuid := self.lookup_sop(sop_ref):
                        meta["ReferencedSeriesUID"] = seriesuid
                case "SEG":
                    if not (sop_refs := meta.get("ReferencedSOPUIDs", [])):
                        continue
                    # this one is a list for SEG
                    # we could just say screw it and take the first one
                    # but we still havent encountered a case where
                    # a seg spans multiple...
                    _all_seg_refs: set[str] = set()
                    for ref in sop_refs:
                        if (
                            seriesuid := self.lookup_sop(ref)
                        ) and seriesuid in self.series_uids:
                            _all_seg_refs.add(seriesuid)
                    if _all_seg_refs:
                        if len(_all_seg_refs) > 1:
                            warnmsg = (
                                f"Multiple series referenced in SEG {meta['SeriesInstanceUID']}"
                                f" ({_all_seg_refs})"
                            )
                            logger.warning(warnmsg)
                        meta["ReferencedSeriesUID"] = _all_seg_refs.pop()
                case "PT":
                    # this is really expensive.... :(
                    # we can probably find a hashmap solution
                    # to speed this up
                    if not (ref_frame := meta.get("FrameOfReferenceUID")):  # fmt: skip
                        continue
                    if ref_series := frame_mapping.get(ref_frame):
                        while ref_series:
                            seriesuid = ref_series.pop()
                            if (
                                seriesuid in self.series_uids
                                and self.series_to_modality(seriesuid) == "CT"
                            ):
                                meta["ReferencedSeriesUID"] = seriesuid
                                break

            # add the metadata to the aggregated db for easy conversion to df
            self._agg_db.append(meta)

    def to_df(self) -> pd.DataFrame:
        """Convert the crawldb to a pandas DataFrame."""
        cleaned_dicts = []

        if not self._agg_db:
            # probably reading from an existing crawldb
            # so we can just iterate over the raw db
            self._agg_db = list(self._metadata_generator())

        for meta in self._agg_db:
            # SR is annoying
            match meta.get("ReferencedSeriesUID", None):
                case [*multiple_refs]:  # SR modality (multiple references)
                    # concatenate them with a "|" pipe
                    ref_series = "|".join(multiple_refs)
                    ref_modality = "|".join(
                        [self.series_to_modality(ref) for ref in multiple_refs]
                    )
                case None:  # no references
                    ref_series = None
                    ref_modality = None
                case one_ref:  # anything but SR modality
                    ref_series = one_ref
                    ref_modality = self.series_to_modality(one_ref)
            cleaned_dicts.append(
                {
                    "PatientID": meta.get("PatientID"),
                    "StudyInstanceUID": meta.get("StudyInstanceUID"),
                    "SeriesInstanceUID": meta.get("SeriesInstanceUID"),
                    "Modality": meta.get("Modality"),
                    "ReferencedModality": ref_modality,
                    "ReferencedSeriesUID": ref_series,
                    "instances": len(meta.get("instances", [])),
                    "folder": meta.get("folder"),
                }
            )

        return pd.DataFrame(cleaned_dicts)


if __name__ == "__main__":
    from rich import print  # noqa: A004, F401

    crawler = Crawler(
        dicom_dir=Path("testdata/Head-Neck-PET-CT"), n_jobs=12, force=True
    )
