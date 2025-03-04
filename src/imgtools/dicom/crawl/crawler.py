from dataclasses import dataclass, field, fields
from pathlib import Path

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

    def remap_refs(self) -> None:
        """Remap references in the database.

        The goal is to get the `ReferencedSeriesUID` for as many series as possible.
        Whereas some series directly reference the `SeriesInstanceUID` of another series,
        others reference one or more `SOPInstanceUID` of instances in another series.
        This method tries to resolve the latter case by mapping the `SOPInstanceUID` to the
        `SeriesInstanceUID` of the series it belongs to.
        """

        # structure of crawldb is : {seriesuid: { subseriesuid: { metadatadictionary } } }
        # structure of sopmap is : { sopuid: seriesuid }

        


if __name__ == "__main__":
    crawler = Crawler(dicom_dir=Path("data"))
