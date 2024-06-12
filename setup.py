from setuptools import setup, find_packages
__version__ = "1.5.4"

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    reqs = fh.read()
    
setup(
    name="med-imagetools",
    version=__version__,
    author="Sejin Kim, Michal Kazmierski, Kevin Qu, Vishwesh Ramanathan, Benjamin Haibe-Kains",
    author_email="benjamin.haibe.kains@utoronto.ca",
    description="Transparent and reproducible image processing pipelines in Python.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bhklab/med-imagetools",
    install_requires=reqs,
    packages=find_packages(),
    extras_require={
        'debug': ['pyvis'],
        'torch': ['torch', 'torchio']
    },
    entry_points={'console_scripts': ['autopipeline = imgtools.autopipeline:main', 'betapipeline = imgtools.autopipeline_refactored:main']},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: Apache Software License",
        "Development Status :: 2 - Pre-Alpha"
    ],
    python_requires='>=3.7',
)
