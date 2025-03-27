from typing import TYPE_CHECKING

from imgtools.dicom.dicom_reader import (
    DicomInput,
    load_rtstruct_dcm,
)
from imgtools.exceptions import (
    RTSTRUCTAttributeError,
)

if TYPE_CHECKING:
    from pydicom.dataset import FileDataset

__all__ = [
    "extract_roi_meta",
    "extract_roi_names",
    "rtstruct_reference_uids",
    "RTSTRUCTRefSeries",
    "RTSTRUCTRefStudy",
    "RTSTRUCTRefSOP",
]


def extract_roi_meta(rtstruct: DicomInput) -> list[dict[str, str]]:
    """Extract ROI metadata from an RTSTRUCT DICOM file.

    Iterate over the `StructureSetROISequence` in the RTSTRUCT file and extract:
        - "ROINumber": Unique identifier for the ROI.
        - "ROIName": Name of the ROI.
        - "ROIGenerationAlgorithm": Algorithm used to generate the ROI.

    Parameters
    ----------
    rtstruct : FileDataset | str | Path | bytes
        Input RTSTRUCT DICOM dataset or file path.

    Returns
    -------
    list of dict[str, str]
        A list of dictionaries, each containing metadata for an ROI.

    Raises
    ------
    RTSTRUCTAttributeError
        If the RTSTRUCT file does not contain the required `StructureSetROISequence`.
    """

    dcm_rtstruct: FileDataset = load_rtstruct_dcm(rtstruct)
    try:
        roi_sequence = dcm_rtstruct.StructureSetROISequence
    except AttributeError as e:
        errmsg = "Failed to extract ROISequence from the RTSTRUCT file."
        raise RTSTRUCTAttributeError(errmsg) from e
    roi_metas = []
    for roi in roi_sequence:
        roi_meta = {}
        roi_meta["ROINumber"] = getattr(roi, "ROINumber", "")
        roi_meta["ROIName"] = getattr(roi, "ROIName", "")
        roi_meta["ROIGenerationAlgorithm"] = getattr(
            roi, "ROIGenerationAlgorithm", ""
        )
        roi_metas.append(roi_meta)
    return roi_metas


def extract_roi_names(rtstruct: DicomInput) -> list[str]:
    """Extract a list of ROI names from an RTSTRUCT DICOM file.

    Parameters
    ----------
    rtstruct : FileDataset | str | Path | bytes
        Input RTSTRUCT DICOM dataset or file path.

    Returns
    -------
    list of str
        A list of ROI names extracted from the RTSTRUCT file.

    Raises
    ------
    RTSTRUCTAttributeError
        If the RTSTRUCT file does not contain the required `StructureSetROISequence`.
    """
    dcm_rtstruct: FileDataset = load_rtstruct_dcm(rtstruct)
    try:
        roi_sequence = dcm_rtstruct.StructureSetROISequence
    except AttributeError as e:
        errmsg = "Failed to extract ROISequence from the RTSTRUCT file."
        raise RTSTRUCTAttributeError(errmsg) from e
    roi_names = [roi.ROIName for roi in roi_sequence]
    return roi_names


class RTSTRUCTRefSeries(str):
    pass


class RTSTRUCTRefStudy(str):
    pass


class RTSTRUCTRefSOP(str):
    pass


def rtstruct_reference_uids(
    rtstruct: DicomInput,
) -> tuple[RTSTRUCTRefSeries, RTSTRUCTRefStudy] | RTSTRUCTRefSOP:
    """Retrieve the referenced SeriesInstanceUID and StudyInstanceUID from an RTSTRUCT.

    Parameters
    ----------
    rtstruct : FileDataset | str | Path | bytes
        Input RTSTRUCT DICOM dataset or file path.

    Returns
    -------
    tuple[RTSTRUCTRefSeries, RTSTRUCTRefStudy]
        - Referenced `SeriesInstanceUID` (RTSTRUCTRefSeries)
        - Referenced `StudyInstanceUID` (RTSTRUCTRefStudy)

    Raises
    ------
    RTSTRUCTAttributeError
        If the RTSTRUCT file does not contain the required reference fields.
    """
    dcm_rtstruct: FileDataset = load_rtstruct_dcm(rtstruct)
    try:
        referenced_series_instance_uid = RTSTRUCTRefSeries(
            dcm_rtstruct.ReferencedFrameOfReferenceSequence[0]
            .RTReferencedStudySequence[0]
            .RTReferencedSeriesSequence[0]
            .SeriesInstanceUID
        )
        referenced_study_instance_uid = RTSTRUCTRefStudy(
            dcm_rtstruct.ReferencedFrameOfReferenceSequence[0]
            .RTReferencedStudySequence[0]
            .ReferencedSOPInstanceUID
        )
        return referenced_series_instance_uid, referenced_study_instance_uid
    except (AttributeError, IndexError) as e:
        errmsg = "Failed to extract Referenced SeriesInstanceUID or Referenced StudyInstanceUID from the RTSTRUCT file."
        errmsg += " Attempting to extract ReferencedSOPInstanceUID."

        try:
            ref_sequence = dcm_rtstruct.ReferencedFrameOfReferenceSequence[0]

            # ref_frame_ref = ref_sequence.FrameOfReferenceUID
            ref_sop = (
                ref_sequence.RTReferencedStudySequence[0]
                .RTReferencedSeriesSequence[0]
                .ContourImageSequence[0]
                .ReferencedSOPInstanceUID
            )

            return RTSTRUCTRefSOP(ref_sop)
        except (AttributeError, IndexError) as e2:
            errmsg += f"First error message: {e}. Second error message: {e2}"
            raise RTSTRUCTAttributeError(errmsg) from e2


if __name__ == "__main__":
    # x = rtstruct_reference_uids(
    #     "/home/gpudual/bhklab/radiomics/Projects/med-imagetools/privatedata/SAR_5SAR2_112001/StudyUID-574.1/RTSTRUCT_Series-59402_SeriesNum-200/RTstruc.dcm"
    # )
    # print(x)
    from tqdm import tqdm

    rtstruct_paths = [
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298041/Study-98.26/RTSTRUCT_Series-15198/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330013/Study-08741/RTSTRUCT_Series-53965/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_409001/Study-07892/RTSTRUCT_Series-41672/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.177354.1023193280.947438293.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_468002/Study-.5591/RTSTRUCT_Series-42409/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178994.1750449150.194674326.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_512003/Study-92083/RTSTRUCT_Series-95543/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179143.1192445894.57260053.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471022/Study-52524/RTSTRUCT_Series-03696/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469023/Study-17445/RTSTRUCT_Series-29681/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179025.9485956.1730554179.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_723004/Study-0.721/RTSTRUCT_Series-54022/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.169385.1011436988.1199944487.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_723004/Study-0.721/RTSTRUCT_Series-54022/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321010/Study-2.651/RTSTRUCT_Series-63240/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178566.918243997.1821533454.part.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321010/Study-2.651/RTSTRUCT_Series-63240/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178566.918243997.1821533454.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_969001/Study-19349/RTSTRUCT_Series-19038/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179337.1873298323.519602601.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_683002/Study-41.17/RTSTRUCT_Series-15730/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179220.63353403.21614732.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191026/Study-20412/RTSTRUCT_Series-78442/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_337003/Study-5.227/RTSTRUCT_Series-56630/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178905.937576541.205890372.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_297005/Study-02230/RTSTRUCT_Series-41254/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168401.338183675.641166357.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_297005/Study-02175/RTSTRUCT_Series-37870/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168398.1852785781.1784202104.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219007/Study-.2114/RTSTRUCT_Series-77987/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469029/Study-13658/RTSTRUCT_Series-44904/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469024/Study-.9347/RTSTRUCT_Series-39494/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471025/Study-82788/RTSTRUCT_Series-26549/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321017/Study-6.241/RTSTRUCT_Series-68189/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178592.84426937.857659987.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_723003/Study-5.835/RTSTRUCT_Series-81835/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179275.1842134644.1291906181.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_683005/Study-1.180/RTSTRUCT_Series-34553/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_337004/Study-2.874/RTSTRUCT_Series-27880/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178907.1271773257.463147148.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191021/Study-10306/RTSTRUCT_Series-89157/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_199002/Study-4.204/RTSTRUCT_Series-39079/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_326007/Study-20608/RTSTRUCT_Series-82399/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178645.2143767342.534068069.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_584007/Study-01640/RTSTRUCT_Series-36197/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179635.1042004666.2065358395.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298031/Study-1.612/RTSTRUCT_Series-12711/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176874.1516586971.347956198.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330014/Study-44017/RTSTRUCT_Series-79093/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_512004/Study-683.1/RTSTRUCT_Series-02616/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179144.126242742.1166210932.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_468005/Study-830.1/RTSTRUCT_Series-11584/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_411007/Study-70258/RTSTRUCT_Series-15722/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_617001/Study-477.0/RTSTRUCT_Series-48415/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179667.489927424.1562513328.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_409006/Study-886.1/RTSTRUCT_Series-14889/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178930.1376827708.1697962492.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191019/Study-43928/RTSTRUCT_Series-69233/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194004/Study-00013/RTSTRUCT_Series-72407/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469016/Study-15502/RTSTRUCT_Series-24386/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179012.768819331.936367893.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471017/Study-35610/RTSTRUCT_Series-90759/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_331007/Study-4.320/RTSTRUCT_Series-22387/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178807.407483006.237832736.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_329006/Study-04185/RTSTRUCT_Series-54951/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178730.35932854.689747552.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_329006/Study-04337/RTSTRUCT_Series-66834/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178731.952126150.1443969239.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_182017/Study-.1100/RTSTRUCT_Series-87463/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176510.1504753956.1673557250.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_685006/Study-15734/RTSTRUCT_Series-66843/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_841001/Study-00007/RTSTRUCT_Series-85138/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191013/Study-00002/RTSTRUCT_Series-71351/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_228008/Study-2.745/RTSTRUCT_Series-92832/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_507003/Study-80799/RTSTRUCT_Series-72123/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198011/Study-64046/RTSTRUCT_Series-30165/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_228002/Study-63.67/RTSTRUCT_Series-34560/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178419.1199488580.1928186674.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_511010/Study-510.7/RTSTRUCT_Series-70173/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179109.281591227.1730440626.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330026/Study-52908/RTSTRUCT_Series-04436/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_113004/Study-69889/RTSTRUCT_Series-51036/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_507009/Study-1.503/RTSTRUCT_Series-42225/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298003/Study-24921/RTSTRUCT_Series-65685/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178446.1453243564.1098959066.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_338005/Study-39225/RTSTRUCT_Series-23753/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.177313.145014385.1685218567.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320004/Study-67146/RTSTRUCT_Series-09810/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178536.1044924907.1090013396.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_686001/Study-60265/RTSTRUCT_Series-26259/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_967007/Study-8.761/RTSTRUCT_Series-66080/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321004/Study-7.447/RTSTRUCT_Series-54334/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178538.1959443503.714715365.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_112004/Study-056.1/RTSTRUCT_Series-44350/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_217001/Study-73284/RTSTRUCT_Series-44894/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178352.565462122.2017264416.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194025/Study-1.801/RTSTRUCT_Series-44097/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_328006/Study-09765/RTSTRUCT_Series-29196/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330007/Study-79560/RTSTRUCT_Series-78525/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.177161.271956585.1839500256.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298022/Study-782.8/RTSTRUCT_Series-32809/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178497.2095035295.1899453530.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_294005/Study-02717/RTSTRUCT_Series-47351/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_182004/Study-.4894/RTSTRUCT_Series-28158/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471004/Study-46385/RTSTRUCT_Series-93183/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179037.768523339.242438254.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194017/Study-82.51/RTSTRUCT_Series-60736/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469005/Study-25310/RTSTRUCT_Series-23738/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_680002/Study-02502/RTSTRUCT_Series-62438/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179187.1347074883.1192824816.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_682005/Study-57241/RTSTRUCT_Series-17687/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_781006/Study-756.1/RTSTRUCT_Series-64088/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298010/Study-12828/RTSTRUCT_Series-82546/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178467.894190789.635092337.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_722003/Study-271.1/RTSTRUCT_Series-90097/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179237.1340231370.2112135448.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320017/Study-61331/RTSTRUCT_Series-85753/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198008/Study-9.315/RTSTRUCT_Series-15188/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_509002/Study-0.616/RTSTRUCT_Series-71456/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_511003/Study-6.686/RTSTRUCT_Series-79647/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179077.796899305.504336057.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_344003/Study-776.1/RTSTRUCT_Series-11969/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198002/Study-0.683/RTSTRUCT_Series-75425/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_507010/Study-3.240/RTSTRUCT_Series-47891/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_200001/Study-15039/RTSTRUCT_Series-91725/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_511009/Study-558.2/RTSTRUCT_Series-44162/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179105.79148081.392196786.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_193007/Study-29568/RTSTRUCT_Series-54195/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_296002/Study-4.317/RTSTRUCT_Series-66044/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178429.1403959485.261262825.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_336004/Study-30822/RTSTRUCT_Series-58103/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178882.1358514420.1887200532.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_680006/Study-80.96/RTSTRUCT_Series-80879/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_331010/Study-07088/RTSTRUCT_Series-63363/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178823.57298632.779113484.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469001/Study-22844/RTSTRUCT_Series-82981/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194013/Study-17694/RTSTRUCT_Series-05983/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_408002/Study-55083/RTSTRUCT_Series-14500/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178927.495563226.691441548.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194019/Study-47516/RTSTRUCT_Series-16082/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_685011/Study-25667/RTSTRUCT_Series-33059/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_294001/Study-00013/RTSTRUCT_Series-84649/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320019/Study-70662/RTSTRUCT_Series-94803/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_193003/Study-160.1/RTSTRUCT_Series-69205/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_781008/Study-02387/RTSTRUCT_Series-11770/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_200005/Study-19008/RTSTRUCT_Series-12137/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178344.621457675.405434241.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198006/Study-33327/RTSTRUCT_Series-37635/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_412004/Study-.3125/RTSTRUCT_Series-47079/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178981.614222800.1974917632.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_511007/Study-2.815/RTSTRUCT_Series-47059/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179094.1198472.1607287428.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_509006/Study-3.996/RTSTRUCT_Series-65459/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179067.598325803.1420894449.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_722007/Study-033.1/RTSTRUCT_Series-79197/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320013/Study-78680/RTSTRUCT_Series-51809/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168605.1139323228.905245295.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298014/Study-7.946/RTSTRUCT_Series-95438/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178477.29574070.1930857247.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_781002/Study-39601/RTSTRUCT_Series-56851/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_682001/Study-64409/RTSTRUCT_Series-72310/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179209.1201779097.1291344694.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_682001/Study-64408/RTSTRUCT_Series-70270/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179208.1486048620.234441751.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_587004/Study-6.575/RTSTRUCT_Series-23719/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179656.225623894.709506390.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194021/Study-18480/RTSTRUCT_Series-16789/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469033/Study-.1449/RTSTRUCT_Series-91078/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_339001/Study-934.1/RTSTRUCT_Series-20253/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_967009/Study-90.99/RTSTRUCT_Series-38911/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_842002/Study-14512/RTSTRUCT_Series-10795/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_967003/Study-8.606/RTSTRUCT_Series-01960/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179329.419381478.840139860.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_619004/Study-0.438/RTSTRUCT_Series-05458/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.177763.986661425.765753410.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330009/Study-01969/RTSTRUCT_Series-61158/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_326010/Study-9.115/RTSTRUCT_Series-66517/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178657.1744285942.1983333062.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_328008/Study-522.1/RTSTRUCT_Series-02841/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_858004/Study-459.1/RTSTRUCT_Series-47939/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179326.1155971152.881289750.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298026/Study-7.449/RTSTRUCT_Series-80626/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178503.1220655766.1285641478.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330003/Study-47632/RTSTRUCT_Series-59576/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178763.2032355793.59710048.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_328002/Study-85094/RTSTRUCT_Series-14399/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178664.232632357.130355625.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191017/Study-95432/RTSTRUCT_Series-18009/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_329008/Study-10188/RTSTRUCT_Series-92872/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178746.1884995170.1506104053.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_331009/Study-96666/RTSTRUCT_Series-72711/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178819.673401840.54693547.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471019/Study-83174/RTSTRUCT_Series-54263/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469018/Study-13653/RTSTRUCT_Series-80778/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_182013/Study-.2712/RTSTRUCT_Series-24619/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_685002/Study-55573/RTSTRUCT_Series-70923/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179226.1832041970.1558701432.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_329002/Study-04543/RTSTRUCT_Series-59888/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178686.1687924886.1401216251.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_329002/Study-05440/RTSTRUCT_Series-61910/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178687.1416347498.1413532564.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_331003/Study-42498/RTSTRUCT_Series-92626/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178794.952782106.8598909.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471013/Study-57194/RTSTRUCT_Series-07285/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_685008/Study-94511/RTSTRUCT_Series-32901/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321021/Study-0.921/RTSTRUCT_Series-45058/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_338001/Study-23627/RTSTRUCT_Series-68738/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178910.1869330455.1112780026.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_781011/Study-85110/RTSTRUCT_Series-76884/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179301.1632846998.1972635594.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298007/Study-7.499/RTSTRUCT_Series-51337/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178458.918467513.1272413969.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330022/Study-21972/RTSTRUCT_Series-75053/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_228006/Study-6.995/RTSTRUCT_Series-51032/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198015/Study-1.113/RTSTRUCT_Series-73983/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_507007/Study-87653/RTSTRUCT_Series-91762/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179062.1589856059.1996278419.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330028/Study-59001/RTSTRUCT_Series-16882/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219004/Study-.5820/RTSTRUCT_Series-03243/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178376.968208930.173970012.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_297006/Study-39008/RTSTRUCT_Series-85637/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_234003/Study-12400/RTSTRUCT_Series-48687/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176977.1849183921.1811433872.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_234003/Study-12618/RTSTRUCT_Series-73248/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168282.70958919.1950122805.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191025/Study-92434/RTSTRUCT_Series-85902/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178221.433931979.1523542373.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191025/Study-92434/RTSTRUCT_Series-85902/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321019/Study-40.50/RTSTRUCT_Series-14680/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178601.1113832743.1922753005.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_683001/Study-5.310/RTSTRUCT_Series-64060/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179217.1683600200.966095380.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321013/Study-6.211/RTSTRUCT_Series-29185/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178578.1126911570.923015920.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_971003/Study-12.10/RTSTRUCT_Series-04813/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_969002/Study-83487/RTSTRUCT_Series-35783/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471021/Study-63475/RTSTRUCT_Series-41136/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469020/Study-14718/RTSTRUCT_Series-70150/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179021.1670230625.1559179209.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_468001/Study-6.669/RTSTRUCT_Series-93550/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_411003/Study-63268/RTSTRUCT_Series-16687/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178958.877574293.1137874276.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_326009/Study-6.506/RTSTRUCT_Series-06303/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178653.245189102.1649291260.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298042/Study-6.965/RTSTRUCT_Series-76300/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176930.85804301.2047315230.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298035/Study-7.524/RTSTRUCT_Series-59477/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176890.430327515.1075281635.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_584003/Study-01398/RTSTRUCT_Series-02327/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179166.1410089216.578376490.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_409008/Study-54873/RTSTRUCT_Series-56550/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178945.124537164.462435828.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_411009/Study-78002/RTSTRUCT_Series-76317/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168803.1090040250.1196103276.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_411009/Study-78002/RTSTRUCT_Series-76317/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_326003/Study-307.1/RTSTRUCT_Series-29455/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178623.31015312.1130686227.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_326003/Study-307.1/RTSTRUCT_Series-41255/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178624.431274280.622796206.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_411004/Study-97226/RTSTRUCT_Series-03035/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178965.1619609933.116699203.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330017/Study-85494/RTSTRUCT_Series-71749/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298032/Study-02511/RTSTRUCT_Series-56440/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176879.548946831.1170109007.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298045/Study-53894/RTSTRUCT_Series-61802/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176941.384779683.423020449.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298045/Study-53894/RTSTRUCT_Series-61802/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176941.384779683.423020449.part.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_584004/Study-00374/RTSTRUCT_Series-79521/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179613.1518814808.2010024995.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298038/Study-0.362/RTSTRUCT_Series-55909/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_619010/Study-93.10/RTSTRUCT_Series-09453/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.177771.2014661297.1258849056.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_326004/Study-8.303/RTSTRUCT_Series-64304/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178630.1572517401.23464782.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_225007/Study-985.4/RTSTRUCT_Series-00026/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178418.948717798.765261428.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219003/Study-269.1/RTSTRUCT_Series-70071/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178374.1459175618.1379123079.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_297001/Study-21327/RTSTRUCT_Series-79284/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178439.617564001.369894185.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_234004/Study-79775/RTSTRUCT_Series-93777/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191022/Study-44429/RTSTRUCT_Series-03864/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_683006/Study-8.981/RTSTRUCT_Series-16170/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191028/Study-44630/RTSTRUCT_Series-16864/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321014/Study-0.343/RTSTRUCT_Series-39189/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178581.549931007.155541588.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469027/Study-18173/RTSTRUCT_Series-81438/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471026/Study-14389/RTSTRUCT_Series-01338/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219009/Study-527.1/RTSTRUCT_Series-91857/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320007/Study-02644/RTSTRUCT_Series-46507/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176964.2052831067.420744759.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_113007/Study-12653/RTSTRUCT_Series-70644/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_511013/Study-198.3/RTSTRUCT_Series-54918/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179124.1712109241.322701251.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330025/Study-36981/RTSTRUCT_Series-56303/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_228001/Study-7.714/RTSTRUCT_Series-50435/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_200011/Study-43108/RTSTRUCT_Series-04608/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178345.2045230099.741121238.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198012/Study-3.916/RTSTRUCT_Series-18657/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191010/Study-53559/RTSTRUCT_Series-32885/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_841002/Study-24164/RTSTRUCT_Series-60644/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_685005/Study-33626/RTSTRUCT_Series-84532/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_182014/Study-11134/RTSTRUCT_Series-54460/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_331004/Study-96650/RTSTRUCT_Series-00943/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178798.1651263502.296638753.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_329005/Study-35250/RTSTRUCT_Series-68118/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178714.162941996.899761419.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_329005/Study-36104/RTSTRUCT_Series-11457/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178715.1589136938.862937337.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194007/Study-6.609/RTSTRUCT_Series-82446/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469015/Study-12438/RTSTRUCT_Series-38143/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179011.1701163863.627929516.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471014/Study-82071/RTSTRUCT_Series-17010/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_858003/Study-489.1/RTSTRUCT_Series-36155/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179323.653311948.1044830356.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298021/Study-4.408/RTSTRUCT_Series-01115/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178495.1389380607.1836308630.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_619009/Study-147.3/RTSTRUCT_Series-72621/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179180.1970192135.847845735.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_328005/Study-7.145/RTSTRUCT_Series-65786/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330004/Study-72815/RTSTRUCT_Series-00489/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178765.924927155.279284879.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_332003/Study-211.1/RTSTRUCT_Series-32772/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178846.1917564169.1977065629.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469034/Study-.9298/RTSTRUCT_Series-64921/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194026/Study-87653/RTSTRUCT_Series-12770/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_217002/Study-84395/RTSTRUCT_Series-27789/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178359.451982582.1340464297.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321007/Study-8.864/RTSTRUCT_Series-29173/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178546.1985955946.558966790.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_967004/Study-95.35/RTSTRUCT_Series-21641/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179332.968208788.2089485888.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219010/Study-9.685/RTSTRUCT_Series-40815/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_686002/Study-15810/RTSTRUCT_Series-84299/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179229.1238023320.1344690418.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_296001/Study-5.619/RTSTRUCT_Series-49475/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178426.598129696.1943956413.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_193004/Study-68137/RTSTRUCT_Series-88091/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298019/Study-3.485/RTSTRUCT_Series-72022/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178491.1216919404.527713607.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198001/Study-85614/RTSTRUCT_Series-72524/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198001/Study-85614/RTSTRUCT_Series-72524/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178328.2125547730.50592946.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_200002/Study-68542/RTSTRUCT_Series-67221/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_509001/Study-4.525/RTSTRUCT_Series-72083/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_200008/Study-50920/RTSTRUCT_Series-52024/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176624.39469519.625590515.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_412003/Study-.2174/RTSTRUCT_Series-12783/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178980.1393803122.931327348.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320014/Study-49166/RTSTRUCT_Series-61383/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.177011.811383709.747793342.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_587003/Study-9.964/RTSTRUCT_Series-00147/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179655.1564230139.1858767967.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_682006/Study-43029/RTSTRUCT_Series-64496/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179216.683560224.1293539362.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_781005/Study-231.1/RTSTRUCT_Series-22719/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298013/Study-9.747/RTSTRUCT_Series-68179/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178474.398308154.844463753.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_680001/Study-18555/RTSTRUCT_Series-05460/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179183.88192363.1625473365.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191009/Study-42249/RTSTRUCT_Series-00704/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179605.1932770344.1296706802.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_972003/Study-10796/RTSTRUCT_Series-52943/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179347.1467465247.1829444274.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471007/Study-30301/RTSTRUCT_Series-59800/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179041.1112493789.184960250.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194014/Study-7.315/RTSTRUCT_Series-46416/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469006/Study-28371/RTSTRUCT_Series-14717/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_182007/Study-.1024/RTSTRUCT_Series-97235/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191003/Study-94812/RTSTRUCT_Series-40033/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_294006/Study-59944/RTSTRUCT_Series-81987/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_112005/Study-63.70/RTSTRUCT_Series-89017/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168053.1802781313.1650233803.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194024/Study-75046/RTSTRUCT_Series-63726/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321005/Study-5.935/RTSTRUCT_Series-42188/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178544.1928376344.1379921836.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_299002/Study-36676/RTSTRUCT_Series-50606/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_299002/Study-16600/RTSTRUCT_Series-14463/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168624.705775273.489837447.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_967006/Study-2.861/RTSTRUCT_Series-01612/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219012/Study-097.1/RTSTRUCT_Series-80552/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168599.1723642073.340177838.dcm.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219012/Study-1.199/RTSTRUCT_Series-28352/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168602.1337020336.1104557645.dcm.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_506002/Study-4.793/RTSTRUCT_Series-15554/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_724001/Study-45520/RTSTRUCT_Series-24735/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179278.930135874.1203443700.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_619001/Study-194.4/RTSTRUCT_Series-14124/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_858001/Study-35018/RTSTRUCT_Series-66034/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179319.1380467526.1697737626.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298029/Study-4.618/RTSTRUCT_Series-57294/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168385.1800294148.565196894.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298023/Study-1.153/RTSTRUCT_Series-65619/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178499.615691482.66803962.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_342001/Study-3.1.1/RTSTRUCT_Series-72205/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178914.264483671.1446097816.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_328007/Study-61225/RTSTRUCT_Series-81081/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330006/Study-99782/RTSTRUCT_Series-70454/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178772.1918940962.261308384.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_972001/Study-01765/RTSTRUCT_Series-73592/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179339.1128182073.418549409.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_680003/Study-01807/RTSTRUCT_Series-27437/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179199.298497810.2020028398.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471005/Study-52024/RTSTRUCT_Series-52702/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194016/Study-86252/RTSTRUCT_Series-62853/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469004/Study-37591/RTSTRUCT_Series-18447/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.177434.1090565061.2102005828.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_319005/Study-807.0/RTSTRUCT_Series-53095/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178526.1039747647.171412645.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_294004/Study-03978/RTSTRUCT_Series-67597/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168377.222476040.364983260.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_296003/Study-41964/RTSTRUCT_Series-92593/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178434.1170452723.1758746446.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_193006/Study-71367/RTSTRUCT_Series-55256/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_336005/Study-71958/RTSTRUCT_Series-81663/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178885.606453199.1704103919.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_722008/Study-746.1/RTSTRUCT_Series-96841/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179261.1221636306.1072257077.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_344002/Study-147.1/RTSTRUCT_Series-21648/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198003/Study-71282/RTSTRUCT_Series-33972/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_511008/Study-814.2/RTSTRUCT_Series-25372/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179096.320293533.972778007.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_507011/Study-36004/RTSTRUCT_Series-16615/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_509003/Study-2.252/RTSTRUCT_Series-54491/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179063.2003286432.1640065409.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198009/Study-58139/RTSTRUCT_Series-00780/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_511002/Study-9.253/RTSTRUCT_Series-29944/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179073.821576980.2107229519.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_412001/Study-379.0/RTSTRUCT_Series-47860/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178968.310620677.2024409099.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_587001/Study-4.160/RTSTRUCT_Series-56116/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179646.1164491666.134741982.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_682004/Study-32099/RTSTRUCT_Series-43948/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_781007/Study-364.1/RTSTRUCT_Series-03237/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298011/Study-20355/RTSTRUCT_Series-36847/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178468.1508329664.295289504.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320016/Study-76730/RTSTRUCT_Series-24904/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_722002/Study-707.1/RTSTRUCT_Series-55690/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179234.541672560.1746914890.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219001/Study-.1986/RTSTRUCT_Series-68979/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178369.592557814.1311562459.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_297003/Study-13265/RTSTRUCT_Series-95671/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178441.1996535710.279744135.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_297003/Study-10647/RTSTRUCT_Series-84453/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178442.364228817.1772958231.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_723002/Study-7.213/RTSTRUCT_Series-99660/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179267.996032815.678323762.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321016/Study-3.857/RTSTRUCT_Series-02124/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178587.1318499518.1549491961.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_683004/Study-983.4/RTSTRUCT_Series-15070/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_413001/Study-607.1/RTSTRUCT_Series-46687/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178990.893210287.784125906.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469025/Study-.7389/RTSTRUCT_Series-80533/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471024/Study-58722/RTSTRUCT_Series-95685/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330015/Study-75677/RTSTRUCT_Series-80680/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178779.221530467.596003729.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_411006/Study-43282/RTSTRUCT_Series-47702/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_468004/Study-6.183/RTSTRUCT_Series-18910/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_409007/Study-30176/RTSTRUCT_Series-45320/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178935.1793933338.696968309.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_584006/Study-00430/RTSTRUCT_Series-36129/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179628.1884114497.718504685.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298030/Study-85.86/RTSTRUCT_Series-97293/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178507.592491443.1448890079.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_973001/Study-52747/RTSTRUCT_Series-57820/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_335002/Study-52090/RTSTRUCT_Series-32451/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178852.831763972.842231548.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_326006/Study-3.532/RTSTRUCT_Series-42970/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178642.1538244374.256599148.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_225005/Study-128.2/RTSTRUCT_Series-51898/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178397.1057440477.1015104057.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_619012/Study-508.4/RTSTRUCT_Series-80537/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179182.1776531709.96952835.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191012/Study-04030/RTSTRUCT_Series-85186/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178145.996887032.211104390.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191012/Study-04030/RTSTRUCT_Series-51865/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178146.714784162.170372396.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_685007/Study-53795/RTSTRUCT_Series-85383/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_182016/Study-.7792/RTSTRUCT_Series-29701/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194005/Study-35952/RTSTRUCT_Series-94238/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469017/Study-.2751/RTSTRUCT_Series-22794/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179016.2101888160.1201097457.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471016/Study-46988/RTSTRUCT_Series-14067/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_331006/Study-89158/RTSTRUCT_Series-53336/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178801.2052110392.1000891422.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_329007/Study-10687/RTSTRUCT_Series-63450/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178741.386549662.285215267.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_343001/Study-500.1/RTSTRUCT_Series-73839/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_322002/Study-94855/RTSTRUCT_Series-70795/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321024/Study-55060/RTSTRUCT_Series-42874/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191018/Study-95611/RTSTRUCT_Series-44092/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_781014/Study-51017/RTSTRUCT_Series-50083/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179317.109201751.1678457809.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_338004/Study-31931/RTSTRUCT_Series-80267/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320005/Study-09890/RTSTRUCT_Series-34290/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178537.1144606060.1355023693.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_228003/Study-68729/RTSTRUCT_Series-66249/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178421.233655021.4518063.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_507008/Study-36044/RTSTRUCT_Series-98970/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_511011/Study-249.5/RTSTRUCT_Series-05436/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179112.669207502.2022526573.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330027/Study-15266/RTSTRUCT_Series-95340/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_228009/Study-73590/RTSTRUCT_Series-21190/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_507002/Study-68818/RTSTRUCT_Series-69638/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198010/Study-51.48/RTSTRUCT_Series-73182/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_781013/Study-10056/RTSTRUCT_Series-90941/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179313.596490341.2017866295.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298005/Study-1.474/RTSTRUCT_Series-44271/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178450.716091501.1128436350.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320002/Study-74775/RTSTRUCT_Series-13622/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_338003/Study-89090/RTSTRUCT_Series-51359/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178912.1380761421.1248937585.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_341001/Study-96799/RTSTRUCT_Series-58942/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_228004/Study-04018/RTSTRUCT_Series-13394/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178422.1230549909.1791648696.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_113008/Study-40193/RTSTRUCT_Series-50253/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_507005/Study-5.951/RTSTRUCT_Series-82775/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_200014/Study-25202/RTSTRUCT_Series-60824/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320008/Study-09805/RTSTRUCT_Series-36458/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178541.2095400182.361351144.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191015/Study-03544/RTSTRUCT_Series-38169/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194008/Study-60099/RTSTRUCT_Series-24160/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_182011/Study-.3794/RTSTRUCT_Series-13133/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471011/Study-47036/RTSTRUCT_Series-24739/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179052.642402472.1619449024.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469010/Study-.5733/RTSTRUCT_Series-83129/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178997.2074983286.1171059761.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_331001/Study-10612/RTSTRUCT_Series-75307/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178782.1598143040.1191542681.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321023/Study-42173/RTSTRUCT_Series-04054/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330012/Study-68683/RTSTRUCT_Series-16751/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_411001/Study-02671/RTSTRUCT_Series-77961/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178947.638337821.1264444340.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_468003/Study-42565/RTSTRUCT_Series-93902/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_512002/Study-182.1/RTSTRUCT_Series-88502/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179134.1015790417.79583289.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_584001/Study-00445/RTSTRUCT_Series-07947/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179152.954577306.1226957401.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298040/Study-86545/RTSTRUCT_Series-65630/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298037/Study-9.414/RTSTRUCT_Series-76216/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_326001/Study-104.1/RTSTRUCT_Series-11883/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178610.614250710.148611426.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219006/Study-6.234/RTSTRUCT_Series-52140/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469028/Study-19514/RTSTRUCT_Series-55557/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191027/Study-42541/RTSTRUCT_Series-24613/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_234001/Study-38851/RTSTRUCT_Series-89305/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168271.109594509.724911697.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_337002/Study-38505/RTSTRUCT_Series-45427/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178899.1410485649.897093680.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321011/Study-40906/RTSTRUCT_Series-99681/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178573.265766953.871018271.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_971001/Study-13210/RTSTRUCT_Series-23186/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_683003/Study-3.540/RTSTRUCT_Series-38879/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179222.816362835.23928491.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471023/Study-67215/RTSTRUCT_Series-35248/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179057.2062203954.708646124.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469022/Study-18750/RTSTRUCT_Series-37155/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179024.2145565480.1498412264.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_193001/Study-.7181/RTSTRUCT_Series-42819/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_336002/Study-75376/RTSTRUCT_Series-90545/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178870.987778416.1609348743.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_336002/Study-57388/RTSTRUCT_Series-77004/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178872.1587720794.1565061274.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_200007/Study-10657/RTSTRUCT_Series-34038/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198004/Study-3.193/RTSTRUCT_Series-57346/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_113011/Study-07588/RTSTRUCT_Series-10366/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_509004/Study-6.373/RTSTRUCT_Series-80889/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179065.1908035111.1263011299.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298016/Study-5.805/RTSTRUCT_Series-26789/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178481.986402550.1548102814.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_682003/Study-10678/RTSTRUCT_Series-32925/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_587006/Study-3.389/RTSTRUCT_Series-58230/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179662.2005775317.1365006705.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_722005/Study-080.1/RTSTRUCT_Series-44462/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179248.1144372850.897768665.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320011/Study-19857/RTSTRUCT_Series-57750/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168558.1420998902.2008322182.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_585001/Study-63532/RTSTRUCT_Series-32162/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179641.1247261502.1913122516.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_680004/Study-36315/RTSTRUCT_Series-87706/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179200.538198120.851847774.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469003/Study-34924/RTSTRUCT_Series-69830/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194011/Study-01450/RTSTRUCT_Series-29109/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471002/Study-99915/RTSTRUCT_Series-94774/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179032.1730301514.360271439.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469009/Study-30860/RTSTRUCT_Series-56664/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_182002/Study-42252/RTSTRUCT_Series-49003/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_319002/Study-625.0/RTSTRUCT_Series-17394/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178513.787170242.1950412164.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471008/Study-04310/RTSTRUCT_Series-13531/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.177575.1700088569.1404602350.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471008/Study-58388/RTSTRUCT_Series-48715/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.177574.185485057.31694512.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_327001/Study-40078/RTSTRUCT_Series-90957/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_294003/Study-03173/RTSTRUCT_Series-81623/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191006/Study-16159/RTSTRUCT_Series-16613/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_976002/Study-92230/RTSTRUCT_Series-48420/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_619006/Study-509.3/RTSTRUCT_Series-69690/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179176.819875812.806061054.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_858006/Study-27347/RTSTRUCT_Series-29654/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298024/Study-26475/RTSTRUCT_Series-69240/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178500.730546892.2018148567.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330001/Study-88343/RTSTRUCT_Series-76808/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178750.1471760273.1056655490.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_112002/Study-0.398/RTSTRUCT_Series-46662/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168049.757906815.1459970657.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_112002/Study-757.1/RTSTRUCT_Series-62185/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176380.513165086.1244585532.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194023/Study-88608/RTSTRUCT_Series-05494/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469031/Study-16032/RTSTRUCT_Series-73832/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_340001/Study-53190/RTSTRUCT_Series-04926/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.177325.1381057769.90204313.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321002/Study-4.718/RTSTRUCT_Series-59249/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_967001/Study-99.55/RTSTRUCT_Series-60633/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321008/Study-4.921/RTSTRUCT_Series-90042/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178560.1589754669.1596757154.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_328004/Study-78917/RTSTRUCT_Series-95068/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178668.1779219338.1681421012.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330005/Study-59357/RTSTRUCT_Series-84747/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178769.1057927920.1184814003.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_323001/Study-3.1.1/RTSTRUCT_Series-97120/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_342002/Study-3.1.1/RTSTRUCT_Series-38299/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178918.941705268.1679944803.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298020/Study-5.528/RTSTRUCT_Series-64699/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178494.1856746547.1584352566.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_858002/Study-48376/RTSTRUCT_Series-47812/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179322.1048463995.1015263847.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_724002/Study-27961/RTSTRUCT_Series-82209/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219011/Study-6.184/RTSTRUCT_Series-33620/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168592.1211909677.74227307.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219011/Study-223.6/RTSTRUCT_Series-60469/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168591.596816784.932773646.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_506001/Study-4.366/RTSTRUCT_Series-75984/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191030/Study-95230/RTSTRUCT_Series-89249/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321006/Study-0.901/RTSTRUCT_Series-30310/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_332002/Study-653.1/RTSTRUCT_Series-43141/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178838.1735804705.1713609213.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_112006/Study-268.1/RTSTRUCT_Series-47790/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_217003/Study-28333/RTSTRUCT_Series-44783/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178365.119751202.569626314.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_722001/Study-923.1/RTSTRUCT_Series-81936/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179232.1022800906.1232748440.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320015/Study-54337/RTSTRUCT_Series-12168/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.168623.1037680034.1697418868.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_682007/Study-07493/RTSTRUCT_Series-98626/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_781004/Study-698.1/RTSTRUCT_Series-86740/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_587002/Study-1.645/RTSTRUCT_Series-94278/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179652.1706508861.384702076.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_587002/Study-1.645/RTSTRUCT_Series-94278/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179652.1706508861.384702076.part.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298012/Study-6.290/RTSTRUCT_Series-42018/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178470.1524320328.4979281.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_511001/Study-0.297/RTSTRUCT_Series-52356/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179068.1106855054.1396273851.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_412002/Study-3.638/RTSTRUCT_Series-13680/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178970.65684835.423439138.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_507012/Study-03631/RTSTRUCT_Series-26104/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_200003/Study-65823/RTSTRUCT_Series-93267/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_344001/Study-48150/RTSTRUCT_Series-65954/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_193005/Study-49713/RTSTRUCT_Series-51690/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298018/Study-3.352/RTSTRUCT_Series-51456/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178489.1482506651.351872285.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_182006/Study-35054/RTSTRUCT_Series-82883/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471006/Study-56404/RTSTRUCT_Series-88710/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194015/Study-8.551/RTSTRUCT_Series-88424/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469007/Study-27105/RTSTRUCT_Series-80423/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191008/Study-31256/RTSTRUCT_Series-76069/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179590.1781577806.1279744029.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_972002/Study-19296/RTSTRUCT_Series-78521/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179340.664515636.424788491.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_619011/Study-925.4/RTSTRUCT_Series-76841/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_326005/Study-47.54/RTSTRUCT_Series-22310/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178640.1019562334.254684357.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_326005/Study-13912/RTSTRUCT_Series-00782/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178639.870953192.1180138793.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_225006/Study-350.4/RTSTRUCT_Series-78217/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178403.710850518.417598361.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298039/Study-0.224/RTSTRUCT_Series-03281/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_335001/Study-89930/RTSTRUCT_Series-44015/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298044/Study-42139/RTSTRUCT_Series-40493/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176940.1853048093.457371300.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298033/Study-0.632/RTSTRUCT_Series-19863/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176881.2016628711.1015349425.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_411005/Study-92390/RTSTRUCT_Series-63735/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178967.596462758.678515721.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_409004/Study-211.1/RTSTRUCT_Series-38366/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330016/Study-74876/RTSTRUCT_Series-16389/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469026/Study-16300/RTSTRUCT_Series-12232/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471027/Study-50613/RTSTRUCT_Series-81403/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_413002/Study-300.1/RTSTRUCT_Series-41580/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.177391.1929202459.1747410826.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219008/Study-153.1/RTSTRUCT_Series-42643/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_683007/Study-9.794/RTSTRUCT_Series-40298/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321015/Study-36010/RTSTRUCT_Series-90676/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178585.689420183.2051304234.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_723001/Study-4.247/RTSTRUCT_Series-29498/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191029/Study-07346/RTSTRUCT_Series-73421/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178231.76631695.711287812.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191023/Study-12720/RTSTRUCT_Series-38470/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_234005/Study-28715/RTSTRUCT_Series-57607/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219002/Study-078.1/RTSTRUCT_Series-50782/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178371.775310169.1938826241.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_507001/Study-58661/RTSTRUCT_Series-08534/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179060.244430238.1955696103.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198013/Study-86407/RTSTRUCT_Series-26225/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_975001/Study-6.3.0/RTSTRUCT_Series-24403/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_511012/Study-200.5/RTSTRUCT_Series-82503/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179118.911035652.1387283372.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330024/Study-81521/RTSTRUCT_Series-52256/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_113006/Study-77296/RTSTRUCT_Series-54396/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298001/Study-9.908/RTSTRUCT_Series-23369/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178444.337164711.762790273.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_322001/Study-50864/RTSTRUCT_Series-28541/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.177083.1234452728.497564847.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_331005/Study-24952/RTSTRUCT_Series-99014/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178800.1571176450.346279579.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_329004/Study-02529/RTSTRUCT_Series-15893/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178707.205307237.1077912853.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469014/Study-30312/RTSTRUCT_Series-81698/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471015/Study-53916/RTSTRUCT_Series-31195/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_182015/Study-.6806/RTSTRUCT_Series-51273/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_685004/Study-61967/RTSTRUCT_Series-31519/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_841003/Study-44150/RTSTRUCT_Series-81402/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179318.1268167810.1196031950.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191011/Study-13550/RTSTRUCT_Series-32517/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321020/Study-7.400/RTSTRUCT_Series-42074/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_329003/Study-.4202/RTSTRUCT_Series-85157/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178692.1659914646.1804338369.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_331002/Study-62775/RTSTRUCT_Series-74977/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178791.548254045.1719796773.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471012/Study-89100/RTSTRUCT_Series-66899/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179055.92847784.1150332888.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469013/Study-.1401/RTSTRUCT_Series-85390/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194001/Study-3.942/RTSTRUCT_Series-87791/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_685009/Study-44969/RTSTRUCT_Series-26421/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_329009/Study-2.1.1/RTSTRUCT_Series-44550/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178749.278741014.139833512.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_331008/Study-07102/RTSTRUCT_Series-48638/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178808.754235854.909200024.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471018/Study-16878/RTSTRUCT_Series-94196/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_182012/Study-.9570/RTSTRUCT_Series-54758/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.30890.1286162724.75639956.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469019/Study-13997/RTSTRUCT_Series-66825/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179020.155826341.913406440.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191016/Study-94039/RTSTRUCT_Series-97751/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198014/Study-4.754/RTSTRUCT_Series-13533/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330029/Study-58574/RTSTRUCT_Series-31489/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_507006/Study-94951/RTSTRUCT_Series-49020/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_113001/Study-64165/RTSTRUCT_Series-39293/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_228007/Study-7.826/RTSTRUCT_Series-76778/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_341002/Study-91867/RTSTRUCT_Series-66652/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_781010/Study-98299/RTSTRUCT_Series-77294/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179293.1353862934.943979222.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298006/Study-00200/RTSTRUCT_Series-47257/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178455.1872708960.1655556240.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471020/Study-19559/RTSTRUCT_Series-08063/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469021/Study-.8250/RTSTRUCT_Series-26297/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_971002/Study-13050/RTSTRUCT_Series-19746/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321012/Study-38538/RTSTRUCT_Series-41424/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178577.1600932633.1879189336.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_969003/Study-55225/RTSTRUCT_Series-06692/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_297007/Study-34880/RTSTRUCT_Series-49370/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321018/Study-68723/RTSTRUCT_Series-30516/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178598.655865761.1439871472.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_191024/Study-05338/RTSTRUCT_Series-43173/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_234002/Study-94965/RTSTRUCT_Series-94397/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_337001/Study-1.880/RTSTRUCT_Series-71034/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178890.637123097.248094175.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_219005/Study-.6415/RTSTRUCT_Series-34883/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_411008/Study-72057/RTSTRUCT_Series-97742/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_225001/Study-037.2/RTSTRUCT_Series-01818/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178377.1346847907.1848512204.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_326002/Study-211.1/RTSTRUCT_Series-95786/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178613.1291733447.534865486.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_584008/Study-01028/RTSTRUCT_Series-28653/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179639.1477854605.875122588.dcm.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298034/Study-5.525/RTSTRUCT_Series-42382/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176887.1565802564.1473672237.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298043/Study-31872/RTSTRUCT_Series-00791/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.176936.1164921026.32756208.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_584002/Study-01789/RTSTRUCT_Series-48664/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179160.1096660500.1200976409.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_411002/Study-25480/RTSTRUCT_Series-35829/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178952.1218465624.1170589100.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_512001/Study-53907/RTSTRUCT_Series-53960/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179132.424756927.1378385285.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_328010/Study-78346/RTSTRUCT_Series-52361/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330011/Study-86624/RTSTRUCT_Series-66014/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_326008/Study-6.191/RTSTRUCT_Series-99075/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178651.1535160636.400517650.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_182001/Study-.3.78/RTSTRUCT_Series-50825/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194018/Study-6.668/RTSTRUCT_Series-96858/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_319001/Study-892.0/RTSTRUCT_Series-05920/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178511.1354450713.70095070.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_331011/Study-35081/RTSTRUCT_Series-40403/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178829.1393576155.518986228.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_513001/Study-815.3/RTSTRUCT_Series-98180/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179150.1911049754.112936734.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194012/Study-9.619/RTSTRUCT_Series-13458/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_471001/Study-75608/RTSTRUCT_Series-40373/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179026.1186612787.481308930.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_585002/Study-77067/RTSTRUCT_Series-31575/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320012/Study-54653/RTSTRUCT_Series-48567/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178570.2021176163.982005349.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_722006/Study-03639/RTSTRUCT_Series-31963/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179258.1931887949.856196249.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298015/Study-96509/RTSTRUCT_Series-19941/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178479.712554145.1502328490.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_587005/Study-3.523/RTSTRUCT_Series-13357/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179659.147080822.1790303663.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_781003/Study-167.1/RTSTRUCT_Series-74336/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179282.459518969.1070977544.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_113012/Study-15021/RTSTRUCT_Series-34540/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_511006/Study-6.386/RTSTRUCT_Series-99294/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179082.569554250.1840774165.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_198007/Study-6.177/RTSTRUCT_Series-25295/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178337.1857205078.1955175164.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_320018/Study-86483/RTSTRUCT_Series-84300/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_781009/Study-66345/RTSTRUCT_Series-31044/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179288.1179824633.864847001.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_193002/Study-81501/RTSTRUCT_Series-68876/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_842003/Study-9.678/RTSTRUCT_Series-92393/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_967002/Study-53.65/RTSTRUCT_Series-21043/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179327.1639335607.1731340146.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_967008/Study-5.750/RTSTRUCT_Series-33948/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_321001/Study-4.119/RTSTRUCT_Series-72497/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_194020/Study-06.57/RTSTRUCT_Series-50894/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_469032/Study-.7247/RTSTRUCT_Series-49237/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330002/Study-54499/RTSTRUCT_Series-19085/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178752.1621015766.1154964590.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_328003/Study-50527/RTSTRUCT_Series-31846/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178665.442647985.598692872.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_298027/Study-8.133/RTSTRUCT_Series-74238/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178505.946946816.567457383.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_858005/Study-68458/RTSTRUCT_Series-58607/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_619005/Study-886.3/RTSTRUCT_Series-80449/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.179173.1839681035.1528723229.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_976001/Study-00917/RTSTRUCT_Series-96142/Subseries-Unknown/RTstruc.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_976001/Study-00917/RTSTRUCT_Series-96142/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.169603.1872149635.35803152.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_330008/Study-61758/RTSTRUCT_Series-57864/Subseries-Unknown/1.2.826.0.1.3680043.9.4183.178778.1924876845.817798252.dcm",
        "/home/gpudual/bhklab/radiomics/Med-ImageNet/rawdata/testdata/Private/SARC021/SAR_5SAR2_328009/Study-54156/RTSTRUCT_Series-14967/Subseries-Unknown/RTstruc.dcm",
    ]

    series_uid_list = []
    sop_uid_list = []
    for path in tqdm(rtstruct_paths):
        match rtstruct_reference_uids(path):
            case RTSTRUCTRefSeries(series_uid), _:
                series_uid_list.append(series_uid)
            case RTSTRUCTRefSOP(sop_uid):
                # print(f"sop_uid: {sop_uido}")
                sop_uid_list.append(sop_uid)
