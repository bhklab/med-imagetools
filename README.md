<div align="center">

# Med-Imagetools: Transparent and Reproducible Medical Image Processing Pipelines in Python


[![CI/CD Status](https://github.com/bhklab/med-imagetools/actions/workflows/main.yml/badge.svg)](https://github.com/bhklab/med-imagetools/actions/workflows/main.yml)
![GitHub repo size](https://img.shields.io/github/repo-size/bhklab/med-imagetools)
![GitHub contributors](https://img.shields.io/github/contributors/bhklab/med-imagetools)
![GitHub stars](https://img.shields.io/github/stars/bhklab/med-imagetools?style=social)
![GitHub forks](https://img.shields.io/github/forks/bhklab/med-imagetools?style=social)
[![Documentation Status](https://readthedocs.org/projects/med-imagetools/badge/?version=documentation)](https://med-imagetools.readthedocs.io/en/documentation/?badge=documentation)
![DOI Status](https://zenodo.org/badge/243786996.svg)

[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/med-imagetools)](https://pypi.org/project/med-imagetools/)
[![GitHub Release](https://img.shields.io/github/v/release/bhklab/med-imagetools?include_prereleases&label=pre-release)](https://github.com/bhklab/med-imagetools/releases)
[![PyPI - Version](https://img.shields.io/pypi/v/med-imagetools?label=stable-pypi)](https://pypi.org/project/med-imagetools/)
[![Docker Pulls](https://img.shields.io/docker/pulls/bhklab/med-imagetools?label=dockerhub-pulls)](https://hub.docker.com/r/bhklab/med-imagetools)
[![Docker Size](https://img.shields.io/docker/image-size/bhklab/med-imagetools/latest?label=docker-size)](https://hub.docker.com/r/bhklab/med-imagetools/tags)

[![PyPI - Format](https://img.shields.io/pypi/format/med-imagetools)](https://pypi.org/project/med-imagetools/)
[![Downloads](https://static.pepy.tech/badge/med-imagetools)](https://pepy.tech/project/med-imagetools)
[![Codecov](https://img.shields.io/codecov/c/github/bhklab/med-imagetools?labelColor=violet&color=white)](https://codecov.io/gh/bhklab/med-imagetools)


**Installation and Usage Documentation**: [https://bhklab.github.io/med-imagetools](https://bhklab.github.io/med-imagetools)

</div>
<!--intro-start-->

## Med-ImageTools core features

Med-Imagetools, a python package offers the perfect tool to transform messy
medical dataset folders to deep learning ready format in few lines of code.
It not only processes DICOMs consisting of different modalities
(like CT, PET, RTDOSE and RTSTRUCTS), it also transforms them into
deep learning ready subject based format taking the dependencies of
these modalities into consideration.  

![cli](assets/imgtools_cli.png)

## Introduction

A medical dataset, typically contains multiple different types of scans
for a single patient in a single study. As seen in the figure below,
the different scans containing DICOM of different modalities are
interdependent on each other. For making effective machine
learning models, one ought to take different modalities into account.

![graph](assets/graph.png)

Fig.1 - Different network topology for different studies of different patients

Med-Imagetools is a unique tool, which focuses on subject
based Machine learning. It crawls the dataset and makes
a network by connecting different modalities present
in the dataset. Based on the user defined modalities,
med-imagetools, queries the graph and process the
queried raw DICOMS. The processed DICOMS are saved as nrrds,
which med-imagetools converts to torchio subject dataset and
eventually torch dataloader for ML pipeline.

## Installing med-imagetools

```console
pip install med-imagetools
imgtools --help
```

```console
uvx --from 'med-imagetools[all]' imgtools --help
```

## Repository Stars

[![Star History Chart](https://api.star-history.com/svg?repos=bhklab/med-imagetools&type=Date)](https://star-history.com/#bhklab/med-imagetools)

## License

This project uses the following license: [MIT License](https://github.com/bhklab/med-imagetools/blob/master/LICENSE)
<!--intro-end-->
