import logging
import os, os.path

import argparse
import datetime

import vtk, qt, ctk, slicer
from DICOMLib import DICOMUtils
import sitkUtils
import SimpleITK as sitk

script_name = "convert_liver_images"
logger = logging.getLogger(script_name)

def get_gtvs(names):
    # Filter the list of segmentations for gtvs based on our discussed
    # rules
    def test(name):
        name = name.lower()
        return ('gtv' in name and not
                ('no' in name or
                 'bowel' in name or
                 'lung' in name or
                 'kidney' in name))

    return list(filter(test, names))

def get_liver_names(names):
    # Filter the list of segmentations for liver masks based on our
    # discussed rules.
    def test(name):
        name = name.lower()
        # Probably a nicer way to write this, but can't be bothered
        # right now.
        if 'liver' in name:
            if 'gtv' in name:
                if 'no' in name:
                    return True
                return False
            if 'rind' in name or 'lesion' in name:
                return False
            return True
        return False

    return list(filter(test, names))

def get_volume_and_segmentation(nodes):
    # Assumes every dicom has _one_ segmentation node, with an
    # associated volume, and returns both
    segs = [n for n in nodes if n.IsA('vtkMRMLSegmentationNode')]
    assert len(segs) == 1
    seg = segs[0]

    ref_vol = seg.GetNodeReference('referenceImageGeometryRef')
    assert ref_vol is not None
    logger.debug(f"type of ref_vol is {type(ref_vol)}")

    return ref_vol, seg

def get_segmentation_names(seg):
    """Get the names of all segments in a vtkMRMLSegmentationNode object"""
    segs = vtk.vtkStringArray()
    seg.GetSegmentation().GetSegmentIDs(segs)
    segs = [segs.GetValue(i) for i in range(segs.GetNumberOfValues())]
    return segs

def list_to_vtkStringArray(strings):
    # Convert a python list of strings to VTK String array.
    out = vtk.vtkStringArray()
    for s in strings:
        out.InsertNextValue(s)
    return out

def segmentation_to_labelmap(segnode, segids, reference=None):
    """Extract a label map from segmentation corresponding to a set of ids.
    """
    strings = list_to_vtkStringArray(segids)
    labelmap = slicer.mrmlScene.CreateNodeByClass('vtkMRMLLabelMapVolumeNode')
    slicer.mrmlScene.AddNode(labelmap)
    segLogic = slicer.modules.segmentations.logic()
    segLogic.ExportSegmentsToLabelmapNode(segnode, strings, labelmap, reference)
    return labelmap

class Output:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        self.format_string = os.path.join(self.output_dir, "{}", "{}.nii.gz")

    def save(self, prop, img, patient_name):
        fname = self.format_string.format(patient_name, prop)
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        sitk.WriteImage(img, fname)

def main():
    # Set up logging
    log_f_name = f"{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}_{script_name}.log"
    logger.setLevel(logging.DEBUG)
    ch = logging.FileHandler(log_f_name)
    ch.setFormatter(logging.Formatter("%(asctime)s - %(name)s:%(levelname)s - %(message)s"))
    logger.addHandler(ch)

    # Set up and parser input args
    parser = argparse.ArgumentParser()
    parser.add_argument("--dicom", required=True)
    parser.add_argument("--output_dir", required=True)
    parser.add_argument("--tmp_db", default="./tmp")
    args = parser.parse_args()

    args.output_dir = os.path.abspath(args.output_dir)
    args.dicom = os.path.abspath(args.dicom)
    args.tmp_db = os.path.abspath(args.tmp_db)

    output = Output(args.output_dir)

    with DICOMUtils.TemporaryDICOMDatabase(args.tmp_db) as db:
        logger.info(f"Starting batch in {args.dicom}")
        # Load all dicom files into db
        DICOMUtils.importDicom(args.dicom, db)
        for patient in db.patients():
            try:
                patient_name = db.nameForPatient(patient)
                logger.info(f"Starting processing of patient {patient_name}")
                opened = DICOMUtils.loadPatientByUID(patient)
                nodes = [slicer.util.getNode(o) for o in opened]
                # from opened need to process items.
                vol, seg = get_volume_and_segmentation(nodes)

                seg_names = get_segmentation_names(seg)
                logger.info(f"Found segmentations {seg_names}")
                gtv_segs = get_gtvs(seg_names)
                logger.info(f"Found gtvs {gtv_segs}")
                liver_segs = get_liver_names(seg_names)
                logger.info(f"Found livers {liver_segs}")

                # Converting data
                logger.info("Pulling data from slicer down to sitk")
                ct = sitkUtils.PullVolumeFromSlicer(vol)
                logger.info("Saving ct")
                output.save('ct', ct, patient_name)

                if len(gtv_segs) > 0:
                    # Convert gtv and liver to label maps
                    logger.info("Creating gtv labelmap")
                    gtvs = segmentation_to_labelmap(seg, gtv_segs, vol)
                    gtv = sitkUtils.PullVolumeFromSlicer(gtvs)
                    gtv = gtv != 0
                    logger.info("Saving gtv mask")
                    output.save('gtv', gtv, patient_name)

                if len(liver_segs) > 0:
                    logger.info("Creating liver labelmap")
                    liver = segmentation_to_labelmap(seg, liver_segs, vol)
                    liver = sitkUtils.PullVolumeFromSlicer(liver)
                    liver = liver != 0
                    logger.info("Saving liver mask")
                    output.save('liver', liver, patient_name)

                if len(liver_segs) > 0 and len(gtv_segs) > 0:
                    liver_sub_gtv = liver & (gtv == 0)
                    logger.info("Saving mask for liver with gtv removed")
                    output.save('liver_sub_gtv', liver_sub_gtv, patient_name)
            except Exception as e:
                patient_name = db.nameForPatient(patient)
                logger.exception(f"Something went wrong with patient {patient_name}")
            finally:
                slicer.mrmlScene.Clear(0)


if __name__=="__main__":
    main()








