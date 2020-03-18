# `imgtools` --- transparent and reproducible image processing pipelines in Python

## Installation
### <recommended> Create new conda virtual environment
```
conda create -n imgtools
```
### Install the required packages

using `conda`:
```
conda install --file requirements.txt
```

using `pip`:
```
python -m pip install -r requirements.txt
```

### Install `imgtools`

```
python -m pip install .
```

## Reporting issues
Please use GitHub issues to report any bugs, user experience/API issues and enhancement proposals. Use the following template while reporting an issue:

#### Description
A brief (1-2 sentences) description of the problem/suggestion.

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

#### System Info
Specify your operating system name and version, and additionally names and versions of all relevant packages. For example,

MacOS 10.13.6  
imgtools alpha-0.1  
Python 3.7.6  
conda 4.8.2  
numpy 1.18.1  
SimpleITK 1.2.4  
pydicom 1.3.0.

You can find the versions of all installed packages using
```
conda list
```

or

```
pip list
```

#### Backtrace
If an error is raised, paste the full traceback here. Use Markdown code blocks to separate the traceback:
````
```
Exception                                 Traceback (most recent call last)
<ipython-input-3-7edcf8a01b74> in <module>
----> 1 raise Exception("This is an error")

Exception: This is an error
```
````
