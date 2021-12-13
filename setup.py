from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    reqs = fh.read()
    
setup(
    name="med-imagetools",
    version="0.2.0",
    author="Michal Kazmierski, Sejin Kim, Vishwesh Ramanathan, Benjamin Haibe-Kains",
    author_email="benjamin.haibe.kains@utoronto.ca",
    description="Transparent and reproducible image processing pipelines in Python.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/bhklab/med-imagetools",
    install_requires=reqs,
    packages=find_packages(),
    extras_require={
        'debug': ['pyvis'],
    },
    # classifiers=[
    #     "Programming Language :: Python :: 3",
    #     "License :: OSI Approved :: MIT License",
    #     "Operating System :: OS Independent",
    # ],
    python_requires='>=3.6',
)
