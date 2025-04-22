# import shutil
# from pathlib import Path

# from rich import print  # noqa
# from tqdm import tqdm

# from imgtools.coretypes.base_masks import VectorMask
# from imgtools.coretypes.imagetypes import Scan
# from imgtools.coretypes.masktypes import (
#     SEG,
#     ROIMatcher,
#     ROIMatchStrategy,
#     RTStructureSet,
# )
# from imgtools.dicom.crawl import Crawler
# from imgtools.dicom.interlacer import Interlacer
# from imgtools.io.writers import ExistingFileMode, NIFTIWriter
# from imgtools.loggers import logger, tqdm_logging_redirect

# if __name__ == "__main__":
#     input_directory = Path("data/RADCURE")
#     output_directory = Path("temp_outputs/seg_testing")

#     shutil.rmtree(
#         output_directory,
#         ignore_errors=True,
#     )
#     mask_writer = NIFTIWriter(
#         root_directory=output_directory,
#         # filename_format="Case_{case_id}_{PatientID}/{Modality}_Series-{SeriesInstanceUID}/{roi_key}__[{roi_names}].nii.gz",
#         filename_format="Case_{case_id}_{PatientID}/{Modality}-{roi_key}__[{roi_names}].nii.gz",
#         existing_file_mode=ExistingFileMode.OVERWRITE,
#         compression_level=5,
#     )
#     ref_image_writer = NIFTIWriter(
#         root_directory=output_directory,
#         # filename_format="Case_{case_id}_{PatientID}/{Modality}_Series-{SeriesInstanceUID}/reference.nii.gz",
#         filename_format="Case_{case_id}_{PatientID}/{Modality}-reference.nii.gz",
#         existing_file_mode=ExistingFileMode.OVERWRITE,
#         compression_level=5,
#     )
#     crawler = Crawler(
#         dicom_dir=input_directory,
#         n_jobs=12,
#     )
#     interlacer = Interlacer(crawl_index=crawler.index)

#     matcher = ROIMatcher(
#         match_map={
#             "GTV": [".*gtv.*"],
#             "PTV": [".*ptv.*"],
#             "CTV": [".*ctv.*"],
#             "Tumor": [".*tumor.*"],
#             "Bladder": [r"bladder.*"],
#             "Brain": [r"brain.*"],
#             "Cochlea": [r"cochlea.*"],
#             "Esophagus": [".*esophagus.*"],
#             "Femur": [r"femur.*"],
#             "Heart": [r"heart.*"],
#             "Ispy": [r".*VOLSER.*"],
#             "Kidney": [r"kidney.*"],
#             "Larynx": [r".*larynx.*"],
#             "Liver": [r"liver.*"],
#             "Lung": [".*lung.*"],
#             "Lymph": [r".*lymph.*"],
#             "Mandible": [r".*mandible.*"],
#             "Nodules": [r".*nodule.*"],
#             "Parotid": [r".*parotid.*"],
#             "Prostate": [r"prostate.*"],
#             "Rectum": [r"rectum.*"],
#             "Reference": [r".*reference.*"],
#             "Spinalcord": [".*cord.*"],
#             "Uterus": [r"uterus.*", "ut.*"],
#         },
#         ignore_case=True,
#         handling_strategy=ROIMatchStrategy.SEPARATE,
#     )
#     branches = [
#         *interlacer.query("CT,SEG"),
#         *interlacer.query("MR,SEG"),
#         *interlacer.query("CT,RTSTRUCT"),
#         *interlacer.query("MR,RTSTRUCT"),
#     ]
#     fails = []

#     with tqdm_logging_redirect():
#         for i, (ct, *seg_rts) in enumerate(
#             tqdm(branches, desc="Processing CT and SEG files")
#         ):
#             ct_node = interlacer.series_nodes[ct["Series"]]
#             ct_folder = input_directory.parent / ct_node.folder
#             # seg_node = interlacer.series_nodes[segs[0]['Series']]
#             scan = Scan.from_dicom(
#                 str(ct_folder),
#                 series_id=ct["Series"],
#             )
#             ref_image_writer.save(
#                 scan,
#                 case_id=f"{i:>04d}",
#                 **scan.metadata,
#             )
#             seg = rt = None
#             for seg_rt in seg_rts:
#                 seg_node = interlacer.series_nodes[seg_rt["Series"]]
#                 seg_folder = input_directory.parent / seg_node.folder
#                 seg_file = list(seg_folder.glob("*.dcm"))[0]

#                 modality_class = (
#                     SEG if seg_rt["Modality"] == "SEG" else RTStructureSet
#                 )
#                 to_vectormask_method = (
#                     VectorMask.from_seg
#                     if seg_rt["Modality"] == "SEG"
#                     else VectorMask.from_rtstruct
#                 )

#                 try:
#                     seg = modality_class.from_dicom(
#                         seg_file,
#                     )
#                     vm = to_vectormask_method(
#                         scan,
#                         seg,  # type: ignore
#                         matcher,
#                     )
#                 except Exception as e:
#                     logger.exception(f"{seg_file} {e} {seg}")
#                     fails.append((i, seg_file, e, seg))

#                 for _index, roi_key, roi_names, mask in vm.iter_masks():
#                     mask_writer.save(
#                         mask,
#                         case_id=f"{i:>04d}",
#                         roi_key=roi_key,
#                         roi_names="|".join(roi_names),
#                         **mask.metadata,
#                     )
