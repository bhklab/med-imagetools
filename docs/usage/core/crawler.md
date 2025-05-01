# Crawler

The `Crawler` in Med-ImageTools has the core responsibility of walking through
a directory and collecting all the dicom files (`.dcm`/`.DCM`), regardless
of the directory structure. 

It was designed to extract as much information as possible from the files,
to build an internal database of the data users have.

## Metadata extraction

As of the 2.0 release, the crawler implements a modality-specific set of
extractions which facilitates: 

1. raw extraction of a DICOM tag (i.e `SeriesInstanceUID`)
2. and possible 'ComputedValue' which requires computation on one or more tags
(i.e `ROINames` in `RTSTRUCT` files are computed from the `ROIContourSequence` tag).

This is done using the [ModalityMedataExtractor][imgtools.dicom.dicom_metadata.extractor_base.ModalityMetadataExtractor] base class, which defines the `base_tags`
that are common to all modalities, and the `computed_tags` which sub-classes
can implement to extract modality-specific information on top of their own `modality_tags`.

See the following api documentation for the supported modalities:

- [CTMetadataExtractor][imgtools.dicom.dicom_metadata.extractors.CTMetadataExtractor]
- [MRMetadataExtractor][imgtools.dicom.dicom_metadata.extractors.MRMetadataExtractor]
- [PTMetadataExtractor][imgtools.dicom.dicom_metadata.extractors.PTMetadataExtractor]
- [SEGMetadataExtractor][imgtools.dicom.dicom_metadata.extractors.SEGMetadataExtractor]
- [RTSTRUCTMetadataExtractor][imgtools.dicom.dicom_metadata.extractors.RTSTRUCTMetadataExtractor]
- [RTDOSEMetadataExtractor][imgtools.dicom.dicom_metadata.extractors.RTDOSEMetadataExtractor]
- [RTPLANMetadataExtractor][imgtools.dicom.dicom_metadata.extractors.RTPLANMetadataExtractor]
- [SRMetadataExtractor][imgtools.dicom.dicom_metadata.extractors.SRMetadataExtractor]

For each of the above modalities, there is a `modality_tags` property that
returns a set of tags that can be directly extracted from the DICOM file.
There also may be a `computed_tags` property that returns a mapping of 
keys defined by Med-ImageTools (i.e `SegSpacing` in the `SEG` extractor)
to a callable function that will compute the value from the DICOM file.

!!! tip "how can I find what tags are extracted?"

    You can view the `modality_tags` and `computed_tags` for each modality
    in the above links, and open the `Souce code` dropdown for each property.

## Assumptions made when crawling

As of 2.0, the crawler makes the following assumptions:

1. All DICOM files within the specified input directory are valid DICOM files.
    That is, they all contain a valid DICOM header and can be read by pydicom.

2. All DICOM files belonging to the same **series** are in the **same directory**.
    This assumption is made, to simplify pointing to a series of files, by 
    just pointing to the directory containing the files.

!!! note

    Though we require that all files in a series are in the same directory,
    we do not require that all files in a directory belong to the same series.
    That is, a directory may contain files from multiple series, and the
    crawler will still be able to extract the series information from each
    file.

## Reference building

One of the main features of Med-ImageTools is building the internal database
of all the complex relationships between DICOM series.
The first step in this process is to extract the necessary information
from each DICOM file, which is modality-specific, and given the evolution of
the DICOM standard, may change over time.

For example, while modern `RTSTRUCT` files contain a `RTReferencedSeriesSequence`
tag that references the `SeriesInstanceUID` of the series that the structure
was derived from, this is not always present in older files.
As such, we have to rely on the `ReferencedSOPInstanceUID` tag, which is a
unique identifier for all the files in the Referenced Series.

During the crawling process, we also build a database that maps each found
DICOM file to its corresponding series `SOPInstanceUID -> SeriesInstanceUID`.

If the `RTSTRUCT` file does not contain the `RTReferencedSeriesSequence`,
we use all the `ReferencedSOPInstanceUID` tags in the file to find the
corresponding seires using the mapping.

After a successful crawl, the `Crawler` will have two database interfaces:

1. `crawl_db`: This is the database that contains all the information
    extracted from the DICOM files.
    It is a dictionary mapping the `SeriesInstanceUID` to all the metadatal
    extracted from the files in the series using the
    [`ModalityMetadataExtractor`][imgtools.dicom.dicom_metadata.extractor_base.ModalityMetadataExtractor]
    extractors.

2. `index`: This is a slimmed database that contains the core metadata
    to build a representation of the data relationships.

    It contains the following information:

    1. `PatientID`
    2. `StudyInstanceUID`
    3. `SeriesInstanceUID`
    4. `SubSeries` (possible unique Acquisition)
    5. `Modality`
    6. `ReferencedModality`
    7. `ReferencedSeriesUID`
    8. `instances` (number of instances in the series)
    9. `folder` (path to the folder containing the series)

These files are stored in a `.imgtools` directory next to the input directory.

That is if the input directory is `/path/to/DICOM_FILES`, the index output files
will be stored in `/path/to/.imgtools/DICOM_FILES`.
