# imgtools: transparent and reproducible medical image processing pipelines in Python

## Installation
### (recommended) Create new conda virtual environment
```
conda create -n imgtools
```
### Install the required packages

using `conda`:
```
conda install --file requirements.txt -c defaults -c conda-forge
```

using `pip`:
```
python -m pip install -r requirements.txt
```

### Install `imgtools`

```
python -m pip install .
```

### (optional) Install in development mode

```
python -m pip install -e .
```

This will install the package in editable mode, so that the installed package will update when the code is changed.

#### Description
Go from messy dataset to analysis-ready Nrrd/NIfTI files in 1 command.

#### Minimal working example
Include a minimal example required to reproduce the issue, if applicable. Keep it brief and as general and abstract as possible. Minimize code specific to your project. Wrap your code in Markdown code blocks.

Example:
````
```python
# your code goes here
from imgtools.ops import resample
resampled_image = resample(image)
```
````

*Observed behaviour:*
Include the output or brief description of what **actually** happens, if applicable. Again, use Markdown code blocks to separate program output:
````
```
>>> resampled_image.GetSpacing()
(1., 1., 1.)
```
````

*Expected behaviour:*
Include a brief description of what you expect to happen, if applicable.
