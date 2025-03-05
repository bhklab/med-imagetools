import itk
from rich import print
import pydicom

itk.ProcessObject.SetGlobalWarningDisplay(False)

namefinder = itk.GDCMSeriesFileNames.New()  # Set up progress observer

namefinder.SetUseSeriesDetails(True)
namefinder.AddSeriesRestriction("0020|0012")  # AcquisitionNumber
namefinder.SetRecursive(True)
namefinder.SetDirectory("data/ISPY2/ISPY2-102011/MR_Series-70445")

scan_map = {
    series_uid: namefinder.GetFileNames(series_uid)
    for series_uid in namefinder.GetSeriesUIDs()
}

print(f"Num Subseries: {len(scan_map)}")

for series, filename_set in scan_map.items():
    print(f"\n{series=} and {len(filename_set)=}")
    # Configure the DICOM reader
    image_io = itk.GDCMImageIO.New()
    image_t = itk.Image[itk.F, 3]
    reader = itk.ImageSeriesReader[image_t].New(
        FileNames=[str(f) for f in filename_set],
        ImageIO=image_io,
    )
    reader.SetMetaDataDictionaryArrayUpdate(True)

    # Read the DICOM series
    reader.Update()
    scan = reader.GetOutput()

    # Retrieve metadata dictionary
    meta_dict = image_io.GetMetaDataDictionary()
    keys = list(meta_dict.GetKeys())  # Get all available DICOM tags

    # Print all metadata key-value pairs
    print(f"\nDICOM Metadata for {series}:")
    for key in keys:
        if meta_dict.HasKey(key):
            # convert the "xxxx|xxxx" key to an integer
            try:
                key_int = int(key.split("|")[0], 16) << 16 | int(
                    key.split("|")[1], 16
                )
            except:
                continue

            human_readable_key = pydicom.datadict.keyword_for_tag(key_int)
            value = meta_dict[key]
            print(f"{human_readable_key}: {value}")
    break
    # print(f"{scan.GetSpacing()=}")
    # print(f"{scan.GetOrigin()=}")
    # print(f"{scan.GetDirection()=}")
    # print(f"{scan.GetLargestPossibleRegion().GetSize()=}")
