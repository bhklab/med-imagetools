# CHANGELOG


## v2.0.0-rc.7 (2025-02-14)

### Bug Fixes

- Update SEG value for ISPY2 dataset in test configuration
  ([`d9a83d1`](https://github.com/bhklab/med-imagetools/commit/d9a83d1b20f93df2a551a56a8646765f3cc5a2c5))


## v2.0.0-rc.6 (2025-02-14)


## v2.0.0-rc.5 (2025-02-14)

### Bug Fixes

- Add function to handle out of bounds coordinates for a RegionBox in an image
  ([#221](https://github.com/bhklab/med-imagetools/pull/221),
  [`fc36464`](https://github.com/bhklab/med-imagetools/commit/fc364640fa9766fb41e1de3db4f1f0add8aebd3b))

This works the same way as `_adjust_negative_coordinates`, but requires the image as an addition
  input and modifies the RegionBox object directly.

A message is logged in the debugger if a dimension is adjusted.

I also updated the `crop_image` function to call this before applying the crop.

- Handle odd extra dimension values in expand_to_min_size
  ([#220](https://github.com/bhklab/med-imagetools/pull/220),
  [`881dcfc`](https://github.com/bhklab/med-imagetools/commit/881dcfc4b53276228cbae2049215592bdff1ca37))

- Removed import
  ([`c9d3b4f`](https://github.com/bhklab/med-imagetools/commit/c9d3b4f94e76154c6ea91d3a2f3eefd20554f5d3))

- Replace Error with ValueError for task ID validation in AutoPipeline
  ([`7d911be`](https://github.com/bhklab/med-imagetools/commit/7d911be62bc4558812bab20b2a0c997068d579f8))

- Update array_to_image function to require either a reference image or all spatial parameters
  ([`e35c842`](https://github.com/bhklab/med-imagetools/commit/e35c842516992df8ea0936b4c5560c503353daa0))

- Update import path for get_modality_metadata in old_loaders.py
  ([`93a16c1`](https://github.com/bhklab/med-imagetools/commit/93a16c140d28b5a4a52ca1fdb5e6cfb21cc32357))

- Update testdata function to accept patterns for exclusion
  ([`d321275`](https://github.com/bhklab/med-imagetools/commit/d321275ee692ae550948d9097f27859672d4a832))

### Chores

- Add Python 3.13 to classifiers and include project URLs in pyproject.toml
  ([`e1eca75`](https://github.com/bhklab/med-imagetools/commit/e1eca7505cdb3189553fa5be4c1d435125872cb5))

- Deprecate
  ([`2d9d86d`](https://github.com/bhklab/med-imagetools/commit/2d9d86da9a8052203d3fc967b77ceab0380ccbc7))

- Deprecate
  ([`e060e79`](https://github.com/bhklab/med-imagetools/commit/e060e794b1b183e78164316651d9e4ca7b6c1577))

- Deprecate
  ([`2123ed8`](https://github.com/bhklab/med-imagetools/commit/2123ed83c8ff298bb3d0c2899e97c8ea527986c1))

- Deprecate autopipeutils and nifti_to_dicom modules
  ([`3cf82c9`](https://github.com/bhklab/med-imagetools/commit/3cf82c9a2375f08bd1c2ce2c7508e994ceca2e1e))

- Import sanitize_file_name and update __all__ to include it
  ([`a28db1d`](https://github.com/bhklab/med-imagetools/commit/a28db1d8a8c812cfd84115c521c707180cd8dbac))

- Ruff qc
  ([`2de2416`](https://github.com/bhklab/med-imagetools/commit/2de2416c3e2b86552d8af67d5b88c3d9094e1ae2))

- Update coverage and mypy configurations to reflect deprecation of modules and increase pytest max
  processes
  ([`bd32522`](https://github.com/bhklab/med-imagetools/commit/bd3252224b69fe4d5653838215c2c2e1a1889c89))

- Update GitHub Actions workflow and modify semantic release configuration
  ([`d622168`](https://github.com/bhklab/med-imagetools/commit/d62216842d43cd19bed185f05a35467b36f917f1))

- Update GitHub Actions workflow to include Python 3.13 and upgrade pixi version to 0.41.1
  ([`1b767e1`](https://github.com/bhklab/med-imagetools/commit/1b767e1cb6cadeafef26e65986c894c1ca7d363a))

- Update GitHub Actions workflow to set locked option to false
  ([`53cc645`](https://github.com/bhklab/med-imagetools/commit/53cc64572ce6a47c803866f020cd273ad89b6490))

- Update pixi toml and lock
  ([`ca942a0`](https://github.com/bhklab/med-imagetools/commit/ca942a0b6f588f1b72746609dc09aab16ac302a4))

- Update pixi.lock to reflect dependency changes
  ([`9982560`](https://github.com/bhklab/med-imagetools/commit/998256015a6c62df3a9d14f6d9439afee73ad558))

### Documentation

- Update README.md so codecov badge takes you to codecov.io
  ([`b39528f`](https://github.com/bhklab/med-imagetools/commit/b39528f5ec03193857dac63884227cb8d0d8523a))

### Features

- Add desired_size to centroid bounding box generation
  ([#219](https://github.com/bhklab/med-imagetools/pull/219),
  [`066844d`](https://github.com/bhklab/med-imagetools/commit/066844df24b615298b91387caf80c0029a375f8e))

In old version, bounding box was a single voxel. Now is expanded to at least the minimum dimension
  default.

- **New Features** - Now, users can optionally specify a desired size when generating image bounding
  boxes for enhanced control.

- **Chores** - Updated the software version from 1.21.1 to 1.22.0.

- Add DICOM metadata extraction functions for various modalities
  ([`fbfb509`](https://github.com/bhklab/med-imagetools/commit/fbfb509a171fe1cf5fcf803004b93f0e439a043f))

- Add index command to crawl and index DICOM images
  ([`0234fe0`](https://github.com/bhklab/med-imagetools/commit/0234fe0cbc2de192ca31e7f378b718c016d2548d))

- Add optional import functionality and clean up dependencies
  ([#217](https://github.com/bhklab/med-imagetools/pull/217),
  [`072e6ce`](https://github.com/bhklab/med-imagetools/commit/072e6ce3920283f0323392d9af934cbd3451d8df))

Introduce optional import functionality for h5py and pynrrd, while removing unused dependencies and
  refactoring the codebase for better maintainability.

- Documentation • Updated installation instructions with new environment setup commands and
  streamlined guidance.

- Refactor • Removed legacy imaging processing and indexing functionalities to simplify the toolset.

- New Features • Enhanced error handling for optional dependencies to offer clearer messaging when
  modules are missing.

- Enhance filename sanitization by removing disallowed characters at the edges and adding
  comprehensive tests
  ([`57283e2`](https://github.com/bhklab/med-imagetools/commit/57283e2067dc00928769bb92454a6148e18503c2))

- Enhance RegionBox to support desired size in from_mask_centroid and adjust bounding box
  calculations
  ([`0e85352`](https://github.com/bhklab/med-imagetools/commit/0e853527d2da2019798863e1485be87158fc970c))

- Improve code structure and refactor image processing utilities
  ([`d036547`](https://github.com/bhklab/med-imagetools/commit/d036547ceac610c17363eb9718a7ad3d4aaeb85f))

- **New Features** - Introduced a new PET image type for enhanced imaging support. - Enabled
  automated dataset indexing and visualization for quicker data previews. - Expanded image
  input/output capabilities with versatile export options. - Enhanced scanning functionality with
  improved metadata and statistics. - Upgraded CLI worker allocation for more reliable performance.

- **Refactor** - Streamlined image processing operations and improved overall code clarity.

- **Tests** - Extended test coverage across image conversion and region handling functions.

### Refactoring

- Remove structureset_helpers module and its utilities
  ([`cc68dc7`](https://github.com/bhklab/med-imagetools/commit/cc68dc7cef399b4bb2cc9ce7faa298d409d49493))

- Simplify type hints and clean up mypy configuration
  ([`7c3c97a`](https://github.com/bhklab/med-imagetools/commit/7c3c97a8b80233552220a91c2771619bd67f94ba))

- Update dataset collections and enhance test coverage for shared data directory
  ([`22c8202`](https://github.com/bhklab/med-imagetools/commit/22c82024ecba911d48d3de8cf8056caaad375664))

### Testing

- Add minimum release version check and improve test readability
  ([`576884b`](https://github.com/bhklab/med-imagetools/commit/576884b64e0eeed29c325f8b3e0d94558a881f31))


## v2.0.0-rc.4 (2025-02-10)

### Bug Fixes

- Add function to handle out of bounds coordinates for a RegionBox in an image
  ([#221](https://github.com/bhklab/med-imagetools/pull/221),
  [`9949a4f`](https://github.com/bhklab/med-imagetools/commit/9949a4fa1463ae2c45acb7282a039333a2960253))

This works the same way as `_adjust_negative_coordinates`, but requires the image as an addition
  input and modifies the RegionBox object directly.

A message is logged in the debugger if a dimension is adjusted.

I also updated the `crop_image` function to call this before applying the crop.


## v2.0.0-rc.3 (2025-02-07)

### Chores

- Update lockfile
  ([`9069f4f`](https://github.com/bhklab/med-imagetools/commit/9069f4fe3bcc2f2344d2e6148cb1b7dd614d09c0))


## v2.0.0-rc.2 (2025-02-07)

### Bug Fixes

- Push release candidates to pypi
  ([`2120f9f`](https://github.com/bhklab/med-imagetools/commit/2120f9f3160f1230f782fd50d209ec69dda653a6))

### Chores

- Comment out PyPI publish step in CI workflow
  ([`c42f5eb`](https://github.com/bhklab/med-imagetools/commit/c42f5eb848b254d2389fe58810f43cce389192b7))

- Update pixi.lock file
  ([`e2c2c5e`](https://github.com/bhklab/med-imagetools/commit/e2c2c5e75d1b30db2f4d4e5edb45cffcdff869ae))

### Features

- Allow CI-CD workflow to run on development branch
  ([`d832db9`](https://github.com/bhklab/med-imagetools/commit/d832db9bf165daefab5c849b16c81493799f89b7))

- Update docs and lockfile
  ([`6e07540`](https://github.com/bhklab/med-imagetools/commit/6e075408fd1ef5e4da4ec84000c558d8fa117e59))


## v2.0.0-rc.1 (2025-02-07)

### Chores

- Update lockfile
  ([`f3c4837`](https://github.com/bhklab/med-imagetools/commit/f3c4837e14ca692f68eba2f0d27c30cab2cf7a7c))

### Features

- Add optional import functionality and clean up dependencies
  ([#217](https://github.com/bhklab/med-imagetools/pull/217),
  [`9efc491`](https://github.com/bhklab/med-imagetools/commit/9efc491ef6e6ded596b7880eca810ce24c8a6647))

Introduce optional import functionality for h5py and pynrrd, while removing unused dependencies and
  refactoring the codebase for better maintainability.

- Documentation • Updated installation instructions with new environment setup commands and
  streamlined guidance.

- Refactor • Removed legacy imaging processing and indexing functionalities to simplify the toolset.

- New Features • Enhanced error handling for optional dependencies to offer clearer messaging when
  modules are missing.


## v1.21.1 (2025-02-06)

### Bug Fixes

- Refactor DICOM utilities and enhance documentation
  ([#216](https://github.com/bhklab/med-imagetools/pull/216),
  [`1ed8de6`](https://github.com/bhklab/med-imagetools/commit/1ed8de6d0f373837a24b36653df30338d66cea0c))

Remove unnecessary sanitization functionality, improve DICOM exception handling, and introduce new
  utilities for loading and extracting ROI metadata. Update documentation to include references for
  the new DICOM utilities.

- **New Features** - Enhanced support for processing various DICOM file formats with improved
  metadata extraction and robust error handling. - Introduced cross-platform support for determining
  optimal file path and filename lengths, along with secure filename sanitization.

- **Refactor** - Streamlined DICOM processing by removing legacy parameters and simplifying function
  interfaces for consistent performance.

- **Tests** - Updated the testing suite for improved type safety and reliability, ensuring smoother
  interactions when handling DICOM files.

### Documentation

- Enhance RegionBox with flexible padding options and module updates
  ([#215](https://github.com/bhklab/med-imagetools/pull/215),
  [`5f38f49`](https://github.com/bhklab/med-imagetools/commit/5f38f4994c14dcabf79a3400000f560de1c798cc))

Introduce the BoxPadMethod enum for padding flexibility in RegionBox. Update import paths and remove
  deprecated modules to streamline the codebase.


## v1.21.0 (2025-02-06)

### Chores

- Update lockfile
  ([`3ff9ca1`](https://github.com/bhklab/med-imagetools/commit/3ff9ca1da86a3f2d481a6fd151dec42b90245836))

### Features

- Improve AbstractBaseWriter with indexing and add docs (#176)
  ([#189](https://github.com/bhklab/med-imagetools/pull/189),
  [`e147629`](https://github.com/bhklab/med-imagetools/commit/e147629c0f2f055d02609cde6f1f2f4be5e260c0))

- **New Features** - Introduced a unified file writing framework that streamlines saving image and
  array data across various formats (e.g., HDF5, NIFTI, NumPy). - Enhanced file handling with
  improved validations for naming, compression levels, and managing existing files, ensuring smooth
  data export and logging.

- **Tests** - Added comprehensive testing to verify file saving operations, error handling, and file
  indexing, ensuring robust performance across different usage scenarios. <!-- end of auto-generated
  comment: release notes by coderabbit.ai -->

### Refactoring

- Remove Vector3D; update Coordinate3D and enhance RegionBox
  ([#210](https://github.com/bhklab/med-imagetools/pull/210),
  [`c16ae7c`](https://github.com/bhklab/med-imagetools/commit/c16ae7c04695e2b5f15d3d8a8fe54209b9024dd7))

Remove the Vector3D class, integrating its functionality into Coordinate3D. Update documentation and
  improve the calculate_image_boundaries function to support world coordinates. Rename variables for
  clarity and consistency.

- **New Features** - Introduced a cropping capability that allows simultaneous cropping of images
  and their corresponding masks. - Added an optional parameter to select the coordinate system when
  computing image boundaries. - Added new functions to retrieve example dataset paths and images.

- **Enhancements** - Improved 3D coordinate operations to now support integer arithmetic as well as
  equality and ordering comparisons. - Updated documentation and diagrams to provide a clearer,
  simplified view of class relationships.

- **Refactor** - Removed a legacy 3D vector type to streamline the available coordinate types.

- **Bug Fixes** - Simplified exception handling and improved clarity in the
  `BoundingBoxOutsideImageError` class.

- **Tests** - Expanded test coverage for the new `Coordinate3D` class, including equality and
  comparison operations, while removing tests for the deprecated `Vector3D`. - Added a new test for
  validating example dataset images.


## v1.20.0 (2025-02-06)

### Features

- Add examples module for image dataset tools
  ([#212](https://github.com/bhklab/med-imagetools/pull/212),
  [`a882574`](https://github.com/bhklab/med-imagetools/commit/a8825741006650fae3f36fd5bbe270768b87965a))

- **New Features** - Introduced new functions for streamlined access to example dataset resources,
  mapping key identifiers to their corresponding file paths and images. - Added a dynamic capability
  to conditionally include functionalities based on the availability of test data. - **Bug Fixes**
  	- Enhanced error handling for missing dataset files. - **Tests** - Added a new test function to
  verify the integrity and presence of example dataset images.


## v1.19.0 (2025-02-04)

### Documentation

- Example usage for functional.py ([#190](https://github.com/bhklab/med-imagetools/pull/190),
  [`c2befdc`](https://github.com/bhklab/med-imagetools/commit/c2befdcbdd49e8683243c3827c50032fcf4a2db6))

- **Chores** - Adjusted internal error handling settings for improved type checking.

- **Documentation** - Enhanced usage guides by adding examples to image processing functions to
  assist with proper implementation.

- **Refactor** - Streamlined parameter annotations and updated return formats across image
  transformation operations for better clarity and consistency.

### Features

- Add custom exceptions and utility functions for RTSTRUCT DICOM handling
  ([#211](https://github.com/bhklab/med-imagetools/pull/211),
  [`0739747`](https://github.com/bhklab/med-imagetools/commit/0739747475b6a59d2c8b49b538abc67c9ade0368))

Introduce custom exceptions and utility functions to improve error handling and data extraction for
  RTSTRUCT DICOM files.

- **New Features** - Introduced enhanced capabilities for processing RTSTRUCT DICOM files, including
  streamlined load operations and extraction of region-of-interest metadata and identifiers. - Added
  robust error handling that clearly notifies users of issues during file processing, improving
  diagnostic feedback. - Expanded the publicly accessible tools to simplify interactions with
  structure set data, enabling more efficient DICOM workflow management. - New exception classes for
  better error categorization related to DICOM processing.


## v1.18.0 (2025-01-31)

### Documentation

- Fix subheading README.md
  ([`18c41b9`](https://github.com/bhklab/med-imagetools/commit/18c41b9387c58629047d2d825980b42886c312cd))

### Features

- Add helper types for 3D spatial operations
  ([#203](https://github.com/bhklab/med-imagetools/pull/203),
  [`ee344d1`](https://github.com/bhklab/med-imagetools/commit/ee344d1b580685dacd18fb577224bd4ffd73b4ca))

- **Documentation** - Added a class inheritance diagram and explanation to the `coretypes` README. -
  Introduced detailed documentation for 3D spatial and image-related types.

- **New Features** 	- Added new classes for 3D geometric operations: 		- `Point3D` 		- `Size3D` 		-
  `Coordinate3D` 		- `Centroid` 		- `BoundingBox` 		- `Direction` 		- `ImageGeometry` 		- `MedImage`
  	- Introduced the `RegionBox` class for handling 3D bounding boxes.

- **Bug Fixes** - Implemented error handling for bounding box operations to ensure valid dimensions.

- **Refactor** 	- Removed existing `Image` class from `types.py`. - Restructured image and geometric
  type handling across multiple modules.

- **Tests** - Introduced a comprehensive test suite for `Vector3D`, `Size3D`, `Coordinate3D`, and
  `Spacing3D` classes.

- **Chores** - Updated linting configuration to include new paths and exclude deprecated files.


## v1.17.1 (2025-01-30)

### Bug Fixes

- Mis-handling of string as roi_name for to_segmentation
  ([#206](https://github.com/bhklab/med-imagetools/pull/206),
  [`358be55`](https://github.com/bhklab/med-imagetools/commit/358be55e6f65cb86eb8d7ba083e5d7debef6ab4a))

Remove unnecessary conversion of `roi_names` from string to list and fix handling when a string is
  passed to the `to_segmentation` function.

fixes #205

- **Improvements** 	- Enhanced input handling for ROI names in the segmentation process. - Improved
  flexibility by allowing both string and list input types for ROI names. - **New Features** - Added
  new test cases to validate the functionality of converting ROI points to segmentation images. -
  **Bug Fixes** 	- Updated test data structures for consistency and accuracy.


## v1.17.0 (2025-01-29)

### Documentation

- Fix readme formatting
  ([`5c76c77`](https://github.com/bhklab/med-imagetools/commit/5c76c77c042b043026cc0abc7508f366416a4365))

### Features

- **tests**: Add test dataset downloading and extraction helpers
  ([#201](https://github.com/bhklab/med-imagetools/pull/201),
  [`95bfca6`](https://github.com/bhklab/med-imagetools/commit/95bfca6977dbd2d7e70f02d3758e6d5dc4d69767))

## Release Notes

- **New Features** - Enhanced dataset downloading functionality with progress tracking and timeout
  management 	- Improved dataset extraction with parallel processing support

- **Improvements** 	- Refined GitHub release management 	- Updated test data handling and fixtures
  	- Improved logging and error handling for dataset operations

- **Changes** 	- Renamed `GitHubReleaseManager` to `MedImageTestData` 	- Updated variable names for
  better clarity in various modules 	- Adjusted DICOM file saving parameters

- **Testing** 	- Added new test cases for dataset integrity and download processes 	- Enhanced type
  annotations and test fixtures

### Refactoring

- Improve code formatting and structure across multiple files
  ([#198](https://github.com/bhklab/med-imagetools/pull/198),
  [`230235f`](https://github.com/bhklab/med-imagetools/commit/230235fa538f986693504260f27e33d11e528165))

- **Style** 	- Reformatted code across multiple files to improve readability. 	- Updated method
  signatures to use multi-line formatting. 	- Adjusted import statements and docstring examples. 	-
  Enhanced clarity in error messages and logging statements.

- **Chores** 	- Updated Ruff linting configuration. 	- Adjusted line length limits in configuration
  files. 	- Expanded files considered for linting. - Enhanced type clarity and readability in GitHub
  dataset management classes. - Modified mypy configuration to change file analysis scope and added
  new sections for specific modules.

- Some changes that will propagate to all branches
  ([#199](https://github.com/bhklab/med-imagetools/pull/199),
  [`df23476`](https://github.com/bhklab/med-imagetools/commit/df23476cbfc3919b6cb701f2980d29069f149d84))

- **Configuration Updates** - Updated coverage configuration to exclude specific files from
  reporting - Adjusted pytest cache directory and coverage settings - Removed mypy unreachable code
  warnings

- **Error Handling** - Enhanced pattern resolution with a new `MissingPlaceholderValueError` -
  Improved error messaging for missing placeholder values

- **Code Quality** - Added type ignore annotations for specific library imports - Minor formatting
  improvements in string representations


## v1.16.0 (2025-01-22)

### Chores

- Update .gitattributes for merge strategies and diff management
  ([#184](https://github.com/bhklab/med-imagetools/pull/184),
  [`8fef781`](https://github.com/bhklab/med-imagetools/commit/8fef781fcc9b3b58f13b76ef4696da8cf61b1a04))

### Continuous Integration

- Update CI workflow and add JUnit test reporting
  ([#192](https://github.com/bhklab/med-imagetools/pull/192),
  [`8ccc0c0`](https://github.com/bhklab/med-imagetools/commit/8ccc0c0e2ac1c755e7f203c24c4d878b4dd3a49e))

- **CI/CD** - Simplified GitHub Actions workflow to focus on main branch - Added JUnit test result
  summary reporting - Enhanced test job error handling

- **Development Tools** - Updated pytest configuration for improved test reporting and caching -
  Refined linting configuration - Added new development task to clean cache and coverage files

### Features

- Add Test Data classes to download from github releases
  ([#194](https://github.com/bhklab/med-imagetools/pull/194),
  [`3385682`](https://github.com/bhklab/med-imagetools/commit/3385682c23ae6b574ff1858e4b014b7de79cbd85))

``` ❯ pixi run -e default imgtools --help Usage: imgtools [OPTIONS] COMMAND [ARGS]...

A collection of tools for working with medical imaging data.

Options: -q, --quiet Suppress all logging except errors, overrides verbosity options. -v, --verbose
  Increase verbosity of logging, overrides environment variable. (0-3: ERROR, WARNING, INFO, DEBUG).
  --version Show the version and exit. -h, --help Show this message and exit.

Commands: dicomsort Sorts DICOM files into directories based on their tags. find-dicoms A tool to
  find DICOM files. ```

versus using `med-imagetools[test]` ``` ❯ pixi run -e dev imgtools --help Usage: imgtools [OPTIONS]
  COMMAND [ARGS]...

Commands: dicomsort Sorts DICOM files into directories based on their tags. find-dicoms A tool to
  find DICOM files. testdata Download test data from the latest GitHub release.

```

- **New Features** 	- Added GitHub release management functionality for medical imaging test data.
  	- Introduced new classes for handling GitHub releases and assets. 	- Implemented methods for
  downloading and extracting test datasets. 	- Enhanced command-line interface with a new command
  for downloading test datasets based on availability. 	- Expanded platform support in project
  configuration.

- **Documentation** 	- Updated README with improved layout and badge presentation. 	- Enhanced
  project configuration in `pyproject.toml` and `pixi.toml`.

- **Tests** 	- Added comprehensive test suite for GitHub release data management. 	- Created
  fixtures and test methods to validate release retrieval and extraction. 	- Enhanced test coverage
  with additional scenarios for error handling.

### Refactoring

- Enhance modules classes; StructureSet, PET, Dose, with factory methods
  ([#185](https://github.com/bhklab/med-imagetools/pull/185),
  [`093eab0`](https://github.com/bhklab/med-imagetools/commit/093eab03f441049f9bec4b457e4e24185218f7d7))

## Walkthrough

This pull request introduces significant refactoring across multiple modules in the image tools
  library, focusing on DICOM reading and processing functions. The changes centralize image reading
  functionality into a new `read_image` utility function in the `utils.py` module, rename several
  method signatures to use a more generic `from_dicom` approach, and improve the handling of DICOM
  metadata across different image types like Dose, PET, and StructureSet. The modifications aim to
  standardize the DICOM reading process and enhance code modularity.

## Changes

| File | Changes | |------|---------| | `src/imgtools/io/loaders/old_loaders.py` | - Updated
  `read_dicom_rtstruct` with optional `roi_name_pattern` parameter<br>- Modified method calls for
  `StructureSet`, `Dose`, and `PET` object creation | | `src/imgtools/modules/dose.py` | - Removed
  local `read_image` function<br>- Renamed `from_dicom_rtdose` to `from_dicom`<br>- Imported
  `read_image` from `.utils` | | `src/imgtools/modules/pet.py` | - Removed local `read_image`
  function<br>- Renamed `from_dicom_pet` to `from_dicom`<br>- Imported `read_image` from `.utils` |
  | `src/imgtools/modules/segmentation.py` | - Added new `from_dicom` class method<br>- Added
  `from_dicom_seg` alias method | | `src/imgtools/modules/structureset.py` | - Added `from_dicom`
  method as alias for `from_dicom_rtstruct`<br>- Reintroduced `roi_names` and `has_roi` methods<br>-
  Renamed `_extract_metadata` to utilize new `RTSTRUCTMetadata` type | |
  `src/imgtools/modules/utils.py` | - Added new `read_image` utility function for DICOM series
  reading |

- Refactor find-dicom logic + docstring formatting, closes #149
  ([#186](https://github.com/bhklab/med-imagetools/pull/186),
  [`da363d6`](https://github.com/bhklab/med-imagetools/commit/da363d62d559d00d4714a25014b6d874de506456))

- **Documentation** 	- Improved docstring formatting for better readability in DICOM-related utility
  functions 	- Enhanced parameter descriptions in documentation

- **Chores** 	- Reformatted code for improved readability 	- Slight modifications to code structure
  without changing core functionality

- Remove unused imports for future re-introduction
  ([#188](https://github.com/bhklab/med-imagetools/pull/188),
  [`cf5cbd0`](https://github.com/bhklab/med-imagetools/commit/cf5cbd02581d30168e261aff37d45a1a2b12d720))


## v1.15.0 (2025-01-17)

### Features

- Refactor io module, introduce new abstract base writer
  ([#181](https://github.com/bhklab/med-imagetools/pull/181),
  [`e04008d`](https://github.com/bhklab/med-imagetools/commit/e04008d2f2a2040f3a1092debca0c69caa180f85))

Co-authored-by: coderabbitai[bot] <136622811+coderabbitai[bot]@users.noreply.github.com>


## v1.14.0 (2025-01-17)

### Features

- Add dockerfile and update lockfile ([#177](https://github.com/bhklab/med-imagetools/pull/177),
  [`6cf5515`](https://github.com/bhklab/med-imagetools/commit/6cf551529ebb7bfb432d868f4859c0631ec413a8))


## v1.13.0 (2025-01-16)

### Features

- Refactor utility modules, add patternresolver, formt
  ([#170](https://github.com/bhklab/med-imagetools/pull/170),
  [`dcc5aad`](https://github.com/bhklab/med-imagetools/commit/dcc5aadc9c053e581877b7561828a97c0de122ec))

Introduce image utilities and a new PatternResolver class, along with updated dependencies and
  configuration adjustments. This enhances the project's capabilities for handling image processing
  and pattern resolution.

## Release Notes

- **New Features** - Added `PatternResolver` for parsing and resolving filename patterns. - Enhanced
  `ImageGeometry` with a spacing attribute. - Introduced a new method to extract ROI names from
  DICOM files.

- **Improvements** - Updated dependency specifications for numpy, pandas, and rich. - Improved code
  formatting across multiple files. - Expanded linting coverage for additional Python files. -
  Enhanced error handling and flexibility in ROI extraction from DICOM files.

- **Documentation** - Improved docstrings and code comments for better readability.

- **Chores** - Updated CI/CD workflow to support additional branches. - Reformatted configuration
  files for consistency. - Removed unused import from the `io` module. - Deleted the `common.py`
  file, removing obsolete functionality.


## v1.12.0 (2025-01-15)

### Features

- Improve structureset and crawl modules, Refactor tests and improve dataset handling
  ([#165](https://github.com/bhklab/med-imagetools/pull/165),
  [`5333a80`](https://github.com/bhklab/med-imagetools/commit/5333a80c6b2242c12d384846a3649a94a9eea60f))


## v1.11.2 (2025-01-15)

### Bug Fixes

- Replaced capturing regex terms with non capturing in datagraph
  ([#162](https://github.com/bhklab/med-imagetools/pull/162),
  [`3237b21`](https://github.com/bhklab/med-imagetools/commit/3237b21957adc5bc3efffe42d589bdeb4f27bc57))


## v1.11.1 (2025-01-11)

### Bug Fixes

- Rounding error in resample function ([#163](https://github.com/bhklab/med-imagetools/pull/163),
  [`f57a747`](https://github.com/bhklab/med-imagetools/commit/f57a7473b2dd5e14b12f4cdd833b9ecc1b60e6ad))

When output_size was not provided to `resample` function, the size was determined based on the
  spacing but was floored. This would sometimes incorrectly shrink the image size. Changed to use
  `np.round` instead.

Additionally, added the `output_size` argument to the `resample` call in the `resize` function. The
  output size is already available in the function as `new_size`, so it doesn't make sense to
  recalculate it in the `resample` function.

<!-- This is an auto-generated comment: release notes by coderabbit.ai -->

## Summary by CodeRabbit

- **Bug Fixes** - Improved image resampling and resizing functions with more precise rounding and
  type handling. - Enhanced parameter validation to ensure consistent integer conversion.

<!-- end of auto-generated comment: release notes by coderabbit.ai -->


## v1.11.0 (2025-01-02)

### Features

- Minor grade refactoring ([#158](https://github.com/bhklab/med-imagetools/pull/158),
  [`0dff0f4`](https://github.com/bhklab/med-imagetools/commit/0dff0f403d802d517614105b50f1c4008945e32d))

Co-authored-by: Joshua Siraj <joshua.siraj@ryerson.ca>

### Refactoring

- Improve logging, logic, and type annotations
  ([#151](https://github.com/bhklab/med-imagetools/pull/151),
  [`ef4d0e7`](https://github.com/bhklab/med-imagetools/commit/ef4d0e7c8f6b5e52c395916d0235645517a7ca03))

- **New Features** - Enhanced logging flexibility with new parameters for specifying logger names. -
  Improved progress reporting in the folder crawling process with descriptive progress bars.

- **Bug Fixes** - Updated error handling for invalid file actions and DICOM tag checks for clearer
  user feedback.

- **Documentation** 	- Improved docstring clarity and formatting across multiple functions.

- **Refactor** 	- Streamlined configuration files for testing and linting processes. - Restructured
  class and function definitions for better readability and maintainability.

- **Style** 	- Consistent formatting applied to function signatures and docstrings.

- Modules/datagraph.py ([#153](https://github.com/bhklab/med-imagetools/pull/153),
  [`41a7c88`](https://github.com/bhklab/med-imagetools/commit/41a7c88992525c8cdfd690ef287ab5f76dc8e588))


## v1.10.1 (2024-12-03)

### Bug Fixes

- Update .gitignore to exclude SQLite and database files
  ([`95a2179`](https://github.com/bhklab/med-imagetools/commit/95a217913798b2f1f4aa2555f1f8fddc65b5b44d))


## v1.10.0 (2024-12-03)

### Features

- Begin indexing database, update find-dicoms cli, add cli documentation
  ([#148](https://github.com/bhklab/med-imagetools/pull/148),
  [`48598e7`](https://github.com/bhklab/med-imagetools/commit/48598e7206c14bcd856e8a64b41cb88369647454))

## Release Notes

- **New Features** - Enhanced `find_dicoms` function to support limiting results and filtering by
  search input.

- **Documentation** - Updated installation instructions and expanded "Getting Started" section in
  the README. - Improved navigation structure in documentation, adding new entries for CLI
  reference.

- **Bug Fixes** - Streamlined error handling and logging for various functions, ensuring clearer
  outputs and improved functionality.

- **Chores** - Updated dependencies and configuration files for better management and performance.


## v1.9.4 (2024-11-29)

### Bug Fixes

- Configure Git credentials for GitHub Actions and update documentation deployment step
  ([`adf4e04`](https://github.com/bhklab/med-imagetools/commit/adf4e0431533d7434780951edd6ec82737cac21e))

- Update GitHub Actions workflow for concurrency and permissions;
  ([`45cddb4`](https://github.com/bhklab/med-imagetools/commit/45cddb4fd65be0df14a7f9d2a28261c5cc36159b))


## v1.9.3 (2024-11-29)

### Bug Fixes

- Improve logging maintainability and temporarily remove json logging configuration
  ([#146](https://github.com/bhklab/med-imagetools/pull/146),
  [`afdcc98`](https://github.com/bhklab/med-imagetools/commit/afdcc98a6f3fbd9e26da579fa39b37de7dbfd600))

Refactor logging code for improved maintainability by temporarily removing JSON logging
  functionality.

Update the .gitignore to exclude .dcm and .sqlite files.

Introduce an environment variable for debug logging and set the default log level based on this
  variable.

## Summary by CodeRabbit

- **New Features** - Introduced a new `LoggingManager` class for structured logging management. -
  Added support for JSON logging configuration (currently commented out). - Added a new environment
  variable for logging level configuration in development. 	- New entries in `.gitignore` to ignore
  `.dcm` and `.sqlite` files. - Enhanced CI/CD pipeline with new jobs for building and publishing
  documentation.

- **Improvements** - Enhanced logging control by utilizing environment variables for log levels. -
  Updated logging directory structure and default log filename for better organization. 	- Improved
  management of logging levels based on verbosity settings.

- **Bug Fixes** - Improved handling of logging level discrepancies with user-specified settings.

- **Documentation** - Updated docstrings and comments for clarity on new logging setup and features.


## v1.9.2 (2024-11-22)

### Bug Fixes

- Pipeline entry no longer needs to manually configure loglevel
  ([`66f8119`](https://github.com/bhklab/med-imagetools/commit/66f8119e6e2e1356c1e3b154e7ad2143cb77ea52))

### Chores

- **deps**: Update med-imagetools to version 1.9.1 and update sha256 checksum
  ([`ab77c58`](https://github.com/bhklab/med-imagetools/commit/ab77c5887e5bb8ae1fa477d2780b94dcdf3297a6))

### Refactoring

- **logging**: Simplify logger configuration and enhance environment variable handling
  ([`c1f624b`](https://github.com/bhklab/med-imagetools/commit/c1f624b7dc14d85176d97bf22918fb2f49dc4a8b))


## v1.9.1 (2024-11-22)

### Bug Fixes

- Downstream bug where datagraph.py was missing from wheel due to data* being ignored in .gitignore
  ([`2dbb245`](https://github.com/bhklab/med-imagetools/commit/2dbb2455e1edcbf663effd8d40b6bff88dc92082))

### Documentation

- Fix broken images
  ([`a7d0e3a`](https://github.com/bhklab/med-imagetools/commit/a7d0e3a70959e9a754efcade9f9f3aa75206c9ad))


## v1.9.0 (2024-11-22)

### Features

- Dicom-finder cli tool, and improve documentation
  ([#142](https://github.com/bhklab/med-imagetools/pull/142),
  [`2981baa`](https://github.com/bhklab/med-imagetools/commit/2981baac719da97d6ec6c3c444c046389d44baf3))

* docs: add mkdocs-include-markdown plugin for Markdown file inclusion

* docs: add tag helpers documentation for DICOM utilities

* docs: add documentation for finding DICOM files

* Update src/imgtools/cli/dicomfind.py

* feat: add regex filtering and improved logging for dicom_finder function

* chore: exclude CLI files from coverage reporting


## v1.8.2 (2024-11-21)

### Bug Fixes

- Update README with new CLI point and reorganize, and formatting
  ([`96c6ab6`](https://github.com/bhklab/med-imagetools/commit/96c6ab60488f97ee3830c7d4be8f96f1ebad0cac))


## v1.8.1 (2024-11-21)

### Bug Fixes

- Common prefix for tree
  ([`a940969`](https://github.com/bhklab/med-imagetools/commit/a94096910b3b95629e96e809ec21a705505fe841))


## v1.8.0 (2024-11-21)

### Features

- Add dicomsorting cli entry
  ([`d435f93`](https://github.com/bhklab/med-imagetools/commit/d435f93f0f2fda67094e4aeaa8a1828a570c534d))


## v1.7.0 (2024-11-19)

### Features

- Implement logging and some standards for ruff config
  ([#134](https://github.com/bhklab/med-imagetools/pull/134),
  [`7c31019`](https://github.com/bhklab/med-imagetools/commit/7c310196f87e4e3ba8503d12c45f799c831954e1))

* feat(logging): add structlog integration with custom processors and example logger

* chore: remove star imports

* feat(lint): update ruff configuration to include new linting rules and extend exclusions

* refactor: update pixi.lock and pixi.toml for ruff command structure and remove unused betapipeline
  entry

* refactor(logging): standardize string quotes and improve logger configuration handling

* feat(logging): integrate structured logging and enhance debug information in AutoPipeline and
  StructureSet

* fix: https://github.com/bhklab/med-imagetools/pull/134#discussion_r1846958744

* fix: https://github.com/bhklab/med-imagetools/pull/134#discussion_r1846958749

* fix: https://github.com/bhklab/med-imagetools/pull/134#discussion_r1846958747

* refactor(logging): streamline logging configuration and ensure log directory creation

* chore: add log files to .gitignore to prevent tracking of generated logs

* fix: Update src/imgtools/logging/__init__.py

Co-authored-by: coderabbitai[bot] <136622811+coderabbitai[bot]@users.noreply.github.com>

* fix: https://github.com/bhklab/med-imagetools/pull/134#discussion_r1847024952

* chore: update .gitignore to include log files in imgtools directory

* feat(datagraph): integrate logging for edge table processing and visualization

* feat(ops): add timing for graph formation and update DataGraph initialization

* chore: rename workflow from Test to CI-CD and restrict push triggers to main branch

* feat(crawl): integrate logging for folder crawling and data saving processes

* fix(structureset): enhance logging for ROI point retrieval errors

* fix(autopipeline): update logger level to use environment variable for flexibility

* fix(logging): streamline error handling for log directory creation

* fix: https://github.com/bhklab/med-imagetools/pull/134#discussion_r1847278305

* refactor(logging): enhance logging configuration and streamline JSON setup

* chore(pixi.lock): add license_family field for clarity

* refactor(logging): enhance LoggingManager with valid log levels and improve JSON logging setup

* refactor(logging): enhance documentation and improve LoggingManager configuration options

* refactor(logging): validate log level assignment before setting self.level

* feat(logging): add mypy and type-checking support; refactor logging manager and improve error
  handling

* refactor(logging): remove unused Optional import from typing

---------


## v1.6.0 (2024-11-15)

### Features

- Transfer project management to Pixi ([#133](https://github.com/bhklab/med-imagetools/pull/133),
  [`a268211`](https://github.com/bhklab/med-imagetools/commit/a26821164b55579aa42e87c28386db6c9398f2d6))

* feat: started port to pixi

* feat: updated test suite for pixi and started refactor of cicd

* build: added coverage to gha

* fix: explicitly direct location of package code and update pixi in pipeline

* fix: added linux to pixi

* chore: update GitHub Actions workflow for improved deployment process

* chore: clean up GitHub Actions workflow by removing commented-out jobs and updating dependencies

* chore: update GitHub Actions workflow to deploy from both main and devel branches, and refresh
  dependencies in pixi.lock

* chore(sem-ver): 1.6.0-rc.1

* fix: update version_toml path in pyproject.toml for semantic release

* chore(sem-ver): 1.6.0-rc.2

* chore: remove requirements.txt file and poetry.lock

* chore: update authors and maintainers in pyproject.toml, and add __version__ in __init__.py

* chore: remove setup.py file as part of project restructuring

* chore: update pixi.lock and add ruff configuration for linting

* chore: fix some recommendations from coderabbit

---------

Co-authored-by: semantic-release <semantic-release>


## v1.5.8 (2024-10-25)

### Bug Fixes

- **datagraph**: Iteration through edge_types wasnt updated for seg
  ([#131](https://github.com/bhklab/med-imagetools/pull/131),
  [`e7cca2a`](https://github.com/bhklab/med-imagetools/commit/e7cca2a8a2542e6f82ddae221b298094ebf3c022))

* fix(datagraph): update edge_types to 8 and handle new edge type for SEG->CT/MR mapping in final
  dataframe processing

* fix(pyproject): update attrs version constraint to allow all 23.x versions and above


## v1.5.7 (2024-10-23)

### Bug Fixes

- Ci-cd - add id in release for pypi step
  ([`7abd175`](https://github.com/bhklab/med-imagetools/commit/7abd175d58894b5ea84448735c4933de4aa156bd))


## v1.5.6 (2024-10-23)

### Bug Fixes

- Update ci to release to pypi
  ([`a92a41f`](https://github.com/bhklab/med-imagetools/commit/a92a41f56ab6d86c68d7657104f8c559b1958ffc))


## v1.5.5 (2024-10-23)

### Bug Fixes

- Remove deprecated pydicom.dicomdir.DicomDir variable type option
  ([#130](https://github.com/bhklab/med-imagetools/pull/130),
  [`56ef37e`](https://github.com/bhklab/med-imagetools/commit/56ef37e492d9a4f287ed9ecb7a1c968caca29726))

* fix: remove deprecated pydicom.dicomdir.DicomDir variable type option

* style: removed Union since dicom_data can only be a FileDataset

* refactor: remove Union import for linting

- Update ci to use semver bot
  ([`98e3bd0`](https://github.com/bhklab/med-imagetools/commit/98e3bd0c93fc2be20c31976092047e7a11db57fb))

### Chores

- #126 update docstring for StructureSetToSegmentation (reopen)
  ([#128](https://github.com/bhklab/med-imagetools/pull/128),
  [`272078c`](https://github.com/bhklab/med-imagetools/commit/272078c937fa62fee20a700150f2ed4da7458720))

* chore: bump artifact action version

* refactor: update StructureSetToSegmentation docstring and remove unused dev group in
  pyproject.toml

* chore: fix download action in workflow to use correct artifact version

* chore: correct instantiation reference and update parameter description in
  StructureSetToSegmentation docstring

* chore: enhance StructureSetToSegmentation docstring to support None as a roi_names option for
  loading all ROIs


## v1.5.4 (2024-06-12)

### Bug Fixes

- License updated to MIT ([#119](https://github.com/bhklab/med-imagetools/pull/119),
  [`6e755dd`](https://github.com/bhklab/med-imagetools/commit/6e755ddc70738da5c7afbced6e061d4e039fbd5f))


## v1.5.3 (2024-06-10)

### Bug Fixes

- Clarified license in README.md ([#118](https://github.com/bhklab/med-imagetools/pull/118),
  [`a4899ca`](https://github.com/bhklab/med-imagetools/commit/a4899ca15924dc9fa19f2e1f3964b7bd6c2e2d35))


## v1.5.2 (2024-05-29)

### Bug Fixes

- Upload latest version to pypi
  ([`1debad3`](https://github.com/bhklab/med-imagetools/commit/1debad3836732faf1a2e3f992a9f1d76943b076e))


## v1.5.1 (2024-05-29)

### Bug Fixes

- Format toml
  ([`269f55d`](https://github.com/bhklab/med-imagetools/commit/269f55db58322dc31a5c44ee5a5e2eb830ed3e4f))


## v1.5.0 (2024-05-29)

### Features

- Update Lock
  ([`26590a0`](https://github.com/bhklab/med-imagetools/commit/26590a09f71c9f797d89f6276aef1c1e416f77dc))

- Update readme
  ([`7cd808e`](https://github.com/bhklab/med-imagetools/commit/7cd808e954ce8e4e1bd8b3dbf1978ba70b0e6713))


## v1.1.0 (2024-05-29)

### Bug Fixes

- Add codecov badge
  ([`f43d042`](https://github.com/bhklab/med-imagetools/commit/f43d04231c76313d86d9e0444a6f1e26ed21b9fc))

- Explicit module to track for code coverage
  ([`f15d45d`](https://github.com/bhklab/med-imagetools/commit/f15d45dd43ef2d8956c0e7cbc91eb7741e9830e3))

### Chores

- Bump version
  ([`58ec67f`](https://github.com/bhklab/med-imagetools/commit/58ec67f1f83eeb1f1ce1b580818f5812e1d04244))

### Features

- Semantic release ([#114](https://github.com/bhklab/med-imagetools/pull/114),
  [`23a2d70`](https://github.com/bhklab/med-imagetools/commit/23a2d700772449837672d671873f9db3c544cd37))

* feat: semantic release

* fix: if statement issue


## v1.0.3 (2022-10-14)
