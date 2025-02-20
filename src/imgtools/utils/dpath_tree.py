import json
from pathlib import Path

import dpath
import dpath.util

path = Path("data") / ".imgtools" / "imgtools_NSCLC-Radiomics.json"

data_dict = json.loads(path.read_text())


value = dpath.get(data_dict, "*/description")
