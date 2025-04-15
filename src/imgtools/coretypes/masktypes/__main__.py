import shutil
from pathlib import Path

from rich import print  # noqa
from tqdm import tqdm

from imgtools.coretypes.base_masks import VectorMask
from imgtools.coretypes.imagetypes import Scan
from imgtools.coretypes.masktypes import SEG, ROIMatcher, RTStructureSet
from imgtools.io.writers import ExistingFileMode, NIFTIWriter
from imgtools.loggers import logger, tqdm_logging_redirect

if __name__ == "__main__":
    shutil.rmtree(
        Path("temp_outputs/seg_testing"),
        ignore_errors=True,
    )
    mask_writer = NIFTIWriter(
        root_directory=Path("temp_outputs/seg_testing"),
        filename_format="Case_{case_id}_{PatientID}/{Modality}_Series-{SeriesInstanceUID}/{roi_key}.nii.gz",
        existing_file_mode=ExistingFileMode.OVERWRITE,
        compression_level=5,
    )
    ref_image_writer = NIFTIWriter(
        root_directory=Path("temp_outputs/seg_testing"),
        filename_format="Case_{case_id}_{PatientID}/{Modality}_Series-{SeriesInstanceUID}/reference.nii.gz",
        existing_file_mode=ExistingFileMode.OVERWRITE,
        compression_level=5,
    )

    from imgtools.dicom.crawl import Crawler, CrawlerSettings
    from imgtools.dicom.interlacer import Interlacer

    directory = Path(
        "/home/gpudual/bhklab/radiomics/Projects/med-imagetools/data"
    )
    crawler = Crawler(
        CrawlerSettings(
            directory,
            n_jobs=12,
        )
    )
    interlacer = Interlacer(crawl_index=crawler.index)

    matcher = ROIMatcher(
        match_map={
            "lung": [".*lung.*"],
            "gtv": [".*gtv.*", ".*tumor.*"],
            "Brain": [r"brain.*"],
            "spinalcord": [".*cord.*"],
            "esophagus": [".*esophagus.*"],
            "Prostate": [r"prostate.*"],
            "Femur": [r"femur.*"],
            "Bladder": [r"bladder.*"],
            "Rectum": [r"rectum.*"],
            "Heart": [r"heart.*"],
            "Liver": [r"liver.*"],
            "Kidney": [r"kidney.*"],
            "Cochlea": [r"cochlea.*"],
            "Uterus": [r"uterus.*", "ut.*"],
            "Nodules": [r".*nodule.*"],
            "lymph": [r".*lymph.*"],
            "ispy": [r".*VOLSER.*"],
            "reference": [r".*reference.*"],
        },
        ignore_case=True,
    )
    branches = [
        *interlacer.query("CT,SEG"),
        *interlacer.query("MR,SEG"),
        *interlacer.query("CT,RTSTRUCT"),
        *interlacer.query("MR,RTSTRUCT"),
    ]
    fails = []

    with tqdm_logging_redirect():
        for i, (ct, *seg_rts) in enumerate(
            tqdm(branches, desc="Processing CT and SEG files")
        ):
            ct_node = interlacer.series_nodes[ct["Series"]]
            ct_folder = directory.parent / ct_node.folder
            # seg_node = interlacer.series_nodes[segs[0]['Series']]
            scan = Scan.from_dicom(
                str(ct_folder),
                series_id=ct["Series"],
            )
            ref_image_writer.save(
                scan,
                case_id=f"{i:>04d}",
                **scan.metadata,
            )
            seg = rt = None
            for seg_rt in seg_rts:
                seg_node = interlacer.series_nodes[seg_rt["Series"]]
                seg_folder = directory.parent / seg_node.folder
                seg_file = list(seg_folder.glob("*.dcm"))[0]

                modality_class = (
                    SEG if seg_rt["Modality"] == "SEG" else RTStructureSet
                )
                to_vectormask_method = (
                    VectorMask.from_seg
                    if seg_rt["Modality"] == "SEG"
                    else VectorMask.from_rtstruct
                )

                try:
                    seg = modality_class.from_dicom(
                        seg_file,
                    )
                    vm = to_vectormask_method(
                        scan,
                        seg,  # type: ignore
                        matcher,
                    )
                except Exception as e:
                    logger.exception(f"{seg_file} {e} {seg}")
                    fails.append((i, seg_file, e, seg))

                for _index, roi_key, roi_names, mask in vm.iter_masks():
                    mask_writer.save(
                        mask,
                        case_id=f"{i:>04d}",
                        roi_key=roi_key,
                        roi_names="|".join(roi_names),
                        **mask.metadata,
                    )
