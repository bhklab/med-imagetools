# Med-Imagetools: Transparent and Reproducible Medical Image Processing Pipelines in Python

<!--- These are examples. See https://shields.io for others or to customize this set of shields. You might want to include dependencies, project status and licence info here --->
![GitHub repo size](https://img.shields.io/github/repo-size/bhklab/med-imagetools)
![GitHub contributors](https://img.shields.io/github/contributors/bhklab/med-imagetools)
![GitHub stars](https://img.shields.io/github/stars/bhklab/med-imagetools?style=social)
![GitHub forks](https://img.shields.io/github/forks/bhklab/med-imagetools?style=social)

Med-Imagetools, a python package offers the perfect tool to transform messy medical dataset folders to deep learning ready format in few lines of code. It not only processes DICOMs consisting of different modalities (like CT, PET, RTDOSE and RTSTRUCTS), it also transforms them into deep learning ready subject based format taking the dependencies of these modalities into consideration.  

## Introduction
A medical dataset, typically contains multiple different types of scans for a single patient in a single study. As seen in the figure below, the different scans containing DICOM of different modalities are interdependent on each other. For making effective machine learning models, one ought to take different modalities into account.

<a href="url"><img src="https://github.com/bhklab/med-imagetools/blob/master/images/graph.png" align="center" width="480" ><figcaption>Fig.1 - Different network topology for different studies of different patients</figcaption></a>  

Med-Imagetools is a unique tool, which focuses on subject based Machine learning. It crawls the dataset and makes a network by connecting different modalities present in the dataset. Based on the user defined modalities, med-imagetools, queries the graph and process the queried raw DICOMS. The processed DICOMS are saved as nrrds, which med-imagetools converts to torchio subject dataset and eventually torch dataloader for ML pipeline.

<a href="url"><img src="https://github.com/bhklab/med-imagetools/blob/master/images/methodology.png" align="center" width="500"><figcaption>Fig.2 - Med-Imagetools start to end pipeline</figcaption></a>  

## Installing med-imagetools

```
pip install med-imagetools
```
### (recommended) Create new conda virtual environment
```
conda create -n mit
conda activate mit
pip install med-imagetools
```

### (optional) Install in development mode

```
conda create -n mit
conda activate mit
pip install -e git+https://github.com/bhklab/med-imagetools.git
```
This will install the package in editable mode, so that the installed package will update when the code is changed.

## Demo
These google collab notebooks will introduce the main functionalities of med-imagetools. More information can be found [here](https://github.com/bhklab/med-imagetools/blob/master/examples/README.md)
#### Tutorial 1: Forming Dataset with med-imagetools Autopipeline

[![Google Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/skim2257/tcia_samples/blob/main/notebooks/Tutorial_1_Forming_Dataset_with_Med_Imagetools.ipynb)

#### Tutorial 2: Machine Learning with med-imagetools and torchio

[![Google Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/skim2257/tcia_samples/blob/main/notebooks/Tutorial_2_Machine_Learning_with_Med_Imagetools_and_torchio.ipynb)

## Getting Started
Med-Imagetools takes two step approch to turn messy medical raw dataset to ML ready dataset.  
1. ***Autopipeline***: Crawls the raw dataset, forms a network and performs graph query, based on the user defined modalities. The relevant DICOMS, get processed and saved as nrrds
    ```
    python imgtools/autopipeline.py\
     [INPUT DIRECTORY] \
     [OUTPUT DIRECTORY] \
     --modalities [str: CT,RTSTRUCT,PT] \
     --spacing [Tuple: (int,int,int)]\
     --n_jobs [int]\
     --visualize [bool: True/False]\
    ```
2. ***class Dataset***: This class converts processed nrrds to torchio subjects, which can be easily converted to torch dataset
    ```
    from imgtools.io import Dataset
    
    subjects = Dataset.load_from_nrrd(output_directory, ignore_multi=True)
    data_set = tio.SubjectsDataset(subjects)
    data_loader = torch.utils.data.DataLoader(data_set, batch_size=4, shuffle=True, num_workers=4)
    ```

## Contributors

Thanks to the following people who have contributed to this project:

* [@mkazmier](https://github.com/mkazmier)
* [@skim2257](https://github.com/skim2257)
* [@Vishwesh4](https://github.com/Vishwesh4)
* [@mnakano](https://github.com/mnakano)

## Contact

If you have any questions/concerns, you can reach the following contributors at sejin.kim@uhnresearch.ca

## License

This project uses the following license: [Apache License 2.0](http://www.apache.org/licenses/)
