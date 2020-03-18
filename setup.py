import setuptools

# with open("README.md", "r") as fh:
#     long_description = fh.read()

setuptools.setup(
    name="imgtools", # Replace with your own username
    version="alpha-0.1",
    author="BHK Lab",
    author_email="michal.kazmierski@uhnresearch.ca",
    description="Transparent and reproducible image processing pipelines in Python.",
    # long_description=long_description,
    # long_description_content_type="text/markdown",
    # url="https://github.com/pypa/sampleproject",
    packages=setuptools.find_packages(),
    # classifiers=[
    #     "Programming Language :: Python :: 3",
    #     "License :: OSI Approved :: MIT License",
    #     "Operating System :: OS Independent",
    # ],
    python_requires='>=3.6',
)
