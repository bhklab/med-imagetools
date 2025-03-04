from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Generator

from tqdm import tqdm

from imgtools.dicom.crawl import parse_dicom_dir
from imgtools.logging import logger


@dataclass
class Crawler:
    dicom_dir: Path
    dcm_extension: str = "dcm"
    n_jobs: int = -1
    force: bool = False
    crawl_json_file: Path | None = None

    # Internal
    _crawl_db: dict = field(init=False)
    _sop_map: dict = field(init=False)
    _metadata_gen: Generator[dict, None, None] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        logger.info(
            "Crawling DICOM directory...",
            **{
                f.name: getattr(self, f.name)
                for f in fields(self)
                if not f.name.startswith("_")
            },
        )
        db_path, crawl_db, sopmap_path, sop_map = parse_dicom_dir(
            dicom_dir=self.dicom_dir,
            extension=self.dcm_extension,
            n_jobs=self.n_jobs,
            force=self.force,
            crawl_json=self.crawl_json_file,
        )
        self._crawl_db = crawl_db
        self._sop_map = sop_map
        logger.info(f"Found {len(crawl_db)} Series in {db_path}")
        logger.info(
            f"Found {len(sop_map)} distinct Instances in {sopmap_path}"
        )

        # initialize metadata generator
        self._metadata_gen = self._metadata_generator()

    def __getitem__(self, seriesuid: str) -> dict:
        return self._crawl_db[seriesuid]

    @property
    def series_uids(self) -> list[str]:
        return list(self._crawl_db.keys())

    def lookup_sop(self, sop_instance_uid: str) -> str | None:
        """Get the SeriesInstanceUID corresponding to a SOPInstanceUID.

        Parameters
        ----------
        sop_instance_uid : str
            The SOPInstanceUID to look up

        Returns
        -------
        str or None
            The SeriesInstanceUID if found, None otherwise

        Examples
        --------
        >>> series_uid = crawler.lookup_sop("1.2.3.4.5")
        """
        return self._sop_map.get(sop_instance_uid)

    def _metadata_generator(self) -> Generator[dict, None, None]:
        """Helper generator to flatten the nested structure of the crawldb."""
        for seriesuid in self.series_uids:
            yield from self._crawl_db[seriesuid].values()

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

    def remap_refs(self) -> None:  # noqa: PLR0912
        """Remap references in the database.

        The goal is to get the `ReferencedSeriesUID` for as many series as possible.
        Whereas some series directly reference the `SeriesInstanceUID` of another series,
        others reference one or more `SOPInstanceUID` of instances in another series.
        This method tries to resolve the latter case by mapping the `SOPInstanceUID` to the
        `SeriesInstanceUID` of the series it belongs to.

        Notes
        -----
        This mutates the metadata dictionaries in the crawldb in place.
        i.e the `ReferencedSeriesUID` field is added to metadata dicts
            in `self._crawl_db` database.
        """

        # structure of crawldb is : {seriesuid: { subseriesuid: { metadatadictionary } } }
        # structure of sopmap is : { sopuid: seriesuid }

        for meta in tqdm(self.metadata_dictionaries):
            if (ref := meta.get("ReferencedSeriesUID")) and ref in self.series_uids:  # fmt: skip
                continue

            # TODO:: RTSTRUCT, RTDOSE, & RTPLAN can all be combined into one case
            #       since they all have a single ReferencedSOPUIDs field
            # but for now....
            match meta["Modality"]:
                case "RTSTRUCT":
                    # sop_ref is a single string for RTSTRUCT
                    if not (sop_ref := meta.get("ReferencedSOPUIDs")):
                        continue
                    if seriesuid := self.lookup_sop(sop_ref):
                        meta["ReferencedSeriesUID"] = seriesuid
                case "SEG":
                    _all_seg_refs: set[str] = set()
                    if not (meta.get("ReferencedSOPUIDs")):
                        continue
                    # this one is a list for SEG
                    for ref in meta.get("ReferencedSOPUIDs", []):
                        if seriesuid := self.lookup_sop(ref):
                            _all_seg_refs.add(seriesuid)
                    if _all_seg_refs:
                        if len(_all_seg_refs) >= 1:
                            # we could raise a warning here??
                            pass
                        if _all_seg_refs.pop() in self.series_uids:
                            meta["ReferencedSeriesUID"] = seriesuid
                case "RTDOSE":
                    if not (sop_ref := meta.get("ReferencedSOPUIDs")):
                        continue
                    if seriesuid := self.lookup_sop(sop_ref):
                        meta["ReferencedSeriesUID"] = seriesuid
                case "RTPLAN":
                    if not (sop_ref := meta.get("ReferencedSOPUIDs")):
                        continue
                    if seriesuid := self.lookup_sop(sop_ref):
                        meta["ReferencedSeriesUID"] = seriesuid


if __name__ == "__main__":
    from rich import print

    crawler = Crawler(dicom_dir=Path("data"))

    crawler.remap_refs()


