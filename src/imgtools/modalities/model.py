from dataclasses import dataclass
import pathlib
import pydicom
from imgtools.logging import logger

@dataclass
class BaseImage:
    filepath: pathlib.Path
    PatientID: str
    StudyInstanceUID: str
    SeriesInstanceUID: str
    SOPInstanceUID: str

    def __init__(self, dsfilepath: pathlib.Path):
        self.filepath = dsfilepath
        ds = pydicom.dcmread(dsfilepath, stop_before_pixels=True)
        try:
            self.PatientID = str(ds.PatientID)
            self.StudyInstanceUID = str(ds.StudyInstanceUID)
            self.SeriesInstanceUID = str(ds.SeriesInstanceUID)
            self.SOPInstanceUID = str(ds.SOPInstanceUID)
        except Exception as e:
            logger.exception('Error parsing DICOM', exc_info=e, extra={'path': dsfilepath})
            raise e
    
    def __repr__(self):
        return f"<{self.__class__.__name__}>"

@dataclass
class CT(BaseImage):
    pass

@dataclass
class RTSTRUCT(BaseImage):
    pass

@dataclass
class RTDOSE(BaseImage):
    pass

@dataclass
class PT(BaseImage):
    pass

@dataclass
class SEG(BaseImage):
    seg: dict
    