# CHANGELOG


## v2.4.0 (2025-05-21)

### Chores

- Update cli help image
  ([`32c6176`](https://github.com/bhklab/med-imagetools/commit/32c617671df4d620c73bb3171667750bea5c0bea))

- Update pixi lock
  ([`13b325f`](https://github.com/bhklab/med-imagetools/commit/13b325f6f27c9e088040f2ae12a8375149833b97))

### Features

- Improve no valid samples w/ more useful info to user
  ([#365](https://github.com/bhklab/med-imagetools/pull/365),
  [`e843a12`](https://github.com/bhklab/med-imagetools/commit/e843a12640a1ab076321562e1aaea06e78c4e88e))

addresses not outputting helpful information on failing to get valid samples #363 , add a bunch of
  helper methods for debugging, and extract success/failure reporting into autopipeline_utils

once we abstract the pipeline logic, we can organize this a bit better

- **New Features** - Added improved error handling with a new exception for cases where no valid
  samples are found during pipeline runs. - Introduced detailed reporting and summary statistics for
  pipeline results, including success and failure rates. - Enhanced the display of DICOM series
  information with rich, user-friendly summaries and a new property listing all valid query paths.

- **Refactor** - Streamlined report generation and result aggregation into reusable components for
  clearer pipeline processing.


## v2.3.0 (2025-05-08)

### Bug Fixes

- Correct formatting of allowed modalities validation in nnUNetPipeline
  ([`5baf828`](https://github.com/bhklab/med-imagetools/commit/5baf82859cea52da0d3c2cc0fc4b23f3a76e28fd))

### Features

- Add nnunet output ([#340](https://github.com/bhklab/med-imagetools/pull/340),
  [`33a3792`](https://github.com/bhklab/med-imagetools/commit/33a37926fdc216f415eeb71b604e6775a6d19b27))

- **New Features** - Introduced a new CLI command for nnUNet pipeline processing with comprehensive
  options for modalities, ROI matching, mask saving, and parallel execution. - Added advanced vector
  mask conversion methods supporting overlap handling and bitmask encoding. - Enabled exporting
  datasets in nnUNet format with configurable mask strategies, metadata embedding, and automated
  generation of preprocessing scripts and dataset JSON files. - Provided utilities to generate
  nnUNet training and preprocessing scripts and dataset configuration files.

- **Documentation** - Clarified documentation on vector mask conversion, explicitly describing
  overlap resolution by label priority.

- **Bug Fixes** - Improved mask overlap detection efficiency by short-circuiting when only one mask
  component exists. <!-- end of auto-generated comment: release notes by coderabbit.ai -->

Co-authored-by: Jermiah Joseph <jermiahjoseph98@gmail.com>

Co-authored-by: Jermiah Joseph <44614774+jjjermiah@users.noreply.github.com>


## v2.2.0 (2025-05-05)

### Chores

- Cleanup ruff config and remove old functional module
  ([`efbfeea`](https://github.com/bhklab/med-imagetools/commit/efbfeea07a2ea7baf9104be958d35cdbb979d344))

- Remove git merge annotations
  ([`5569eb2`](https://github.com/bhklab/med-imagetools/commit/5569eb268a4beaebef42ebb564e84aaa50931dd4))

- Update lockfile
  ([`1485171`](https://github.com/bhklab/med-imagetools/commit/1485171e9511bf50ef88f20ab028b5d533d8e56a))

### Code Style

- Ruff check
  ([`8030aba`](https://github.com/bhklab/med-imagetools/commit/8030aba4f4bc64dfc3f294bcf66393f7aa07e1c4))

### Continuous Integration

- Update ruff format command params
  ([`04ecd23`](https://github.com/bhklab/med-imagetools/commit/04ecd235906963f686319eff18f400b5b8c95f7c))

### Features

- Release on PyPi
  ([`94f1304`](https://github.com/bhklab/med-imagetools/commit/94f1304b90d01db44d867eacbb6ff1820b7100f0))


## v2.1.0 (2025-05-05)

### Chores

- Prepare 2.0 release
  ([`c33dfd7`](https://github.com/bhklab/med-imagetools/commit/c33dfd7efc6e2924dd4db994643a42e2fdb43d65))

- Update pixi.lock file
  ([`1d080b0`](https://github.com/bhklab/med-imagetools/commit/1d080b002b2b4172af531f1acf1de1dccd87d0bd))

- Update pixi.lock file
  ([`f3ff708`](https://github.com/bhklab/med-imagetools/commit/f3ff70822e579676b426d5ad915ea1a771f0d5ce))

### Continuous Integration

- Merge termshot action into main workflow
  ([`f9bfc40`](https://github.com/bhklab/med-imagetools/commit/f9bfc4052751d42e4eed26a297946ccdfd293224))

### Documentation

- Add interlacer html demo to website
  ([`bee79d4`](https://github.com/bhklab/med-imagetools/commit/bee79d44f03da339f5fb04d4e18ee2a35b59d9da))


## v2.0.0-rc.32 (2025-05-01)

### Chores

- Update cli help image
  ([`fada490`](https://github.com/bhklab/med-imagetools/commit/fada49011bc061ced2d8403790b8c31fb8ff8408))

### Documentation

- Add AutoPipeline documentation and core module details
  ([#348](https://github.com/bhklab/med-imagetools/pull/348),
  [`1a489a6`](https://github.com/bhklab/med-imagetools/commit/1a489a6ded16ed2a05509998de8b82ec1089cb0d))

Comprehensive documentation for AutoPipeline has been introduced, detailing its functionality in
  medical image processing. This includes usage examples, command line interface instructions, and
  separate documentation for the Crawler and Interlacer modules. A navigation structure for core
  documentation pages has also been established.

### Features

- Add github actions to update cli screenshot png
  ([#347](https://github.com/bhklab/med-imagetools/pull/347),
  [`88fe4c0`](https://github.com/bhklab/med-imagetools/commit/88fe4c00a3675e707f742101e1b2bc1cf400786d))


## v2.0.0-rc.31 (2025-05-01)

### Chores

- Remove Test-PyPI job from CI/CD workflow
  ([`f664644`](https://github.com/bhklab/med-imagetools/commit/f664644395479ba5fc79af8c8eb40c09b76e2e50))

- Update classifiers in pyproject.toml for better project categorization
  ([`2780ebc`](https://github.com/bhklab/med-imagetools/commit/2780ebc2db36fa890712d9b97d00468bfdf95aec))

- Update lockfile
  ([`6e97c7c`](https://github.com/bhklab/med-imagetools/commit/6e97c7c1bb9c6168ee6cf2d970d300edf4db6160))

- Update README.md with docker info
  ([`d83e5b9`](https://github.com/bhklab/med-imagetools/commit/d83e5b99eff3dc34fb3cdaf7275aad5a7ceef65e))

### Documentation

- Add MkDocs hooks for asset management during build process
  ([`4e64438`](https://github.com/bhklab/med-imagetools/commit/4e64438c50f062739c36fc3d883a84db2bc75027))

- Fix typos/formatting/grammar in docs
  ([`5eab61e`](https://github.com/bhklab/med-imagetools/commit/5eab61e626eca827134f3592e7eab089ec500512))

### Features

- Add interlacer cli command for visualizing DICOM series relationships and update documentation
  ([`84cc9e0`](https://github.com/bhklab/med-imagetools/commit/84cc9e0ef0a9376b4b09731523a2706665b05c1e))

### Refactoring

- Remove doc hooks, dont reference readme in docs landing page
  ([`e8d82a6`](https://github.com/bhklab/med-imagetools/commit/e8d82a6df3ca1b1c02b1496baf12c4db2b644901))


## v2.0.0-rc.30 (2025-04-30)

### Chores

- Qc
  ([`cc3aca4`](https://github.com/bhklab/med-imagetools/commit/cc3aca4b756821dd2b41d7ccb44da8e644c8a84b))

- Remove 'readii' from known-first-party in isort configuration
  ([`9e33870`](https://github.com/bhklab/med-imagetools/commit/9e3387097280234b917202be4ecf347845239ea4))

### Documentation

- Update README with imgtools screenshot ([#343](https://github.com/bhklab/med-imagetools/pull/343),
  [`a1dc944`](https://github.com/bhklab/med-imagetools/commit/a1dc944956e2899afe735890a10df8a4bc92238d))

### Features

- Add simplified index file generation and more information in fingerprints
  ([`1fb0b1e`](https://github.com/bhklab/med-imagetools/commit/1fb0b1e6cb9e46681763a6e22663793c94c3bd06))

### Refactoring

- Streamline ruff commands and update linting configuration
  ([`88ce5d8`](https://github.com/bhklab/med-imagetools/commit/88ce5d88e42633bd509dc29c82d0772867c2c009))


## v2.0.0-rc.29 (2025-04-30)

### Bug Fixes

- Update test_invalid_dicom_file to use temporary path for invalid DICOM file
  ([`ccc1ef5`](https://github.com/bhklab/med-imagetools/commit/ccc1ef59a84ed37ec1ffa4f93ca800c247ddd4a8))


## v2.0.0-rc.28 (2025-04-30)

### Bug Fixes

- Update CI-CD workflow to correct job dependencies and conditions for linting and publishing
  ([`9f3bab4`](https://github.com/bhklab/med-imagetools/commit/9f3bab44ea13e8fb87346d24ecf177559c64d839))

### Continuous Integration

- Update CI-CD workflow to include push triggers for development and main branches
  ([`7f734de`](https://github.com/bhklab/med-imagetools/commit/7f734deda47f6710227e3c023639be72578b0eb8))

### Features

- Robust test suite and github action workflow
  ([#341](https://github.com/bhklab/med-imagetools/pull/341),
  [`ad89e48`](https://github.com/bhklab/med-imagetools/commit/ad89e481dbd7669085ec8303fb8aba5037c4c56b))

move unittests into its own directory

now can run

``` pytest -m unittests ```

or

``` pytest -m "not unittests" ```

which will speed things up

will also specify `e2e`, `integration` and `regression` tests

- **New Features** - Added integration tests for CLI commands, including `autopipeline`,
  `dicomsort`, and `index`, to ensure correct behavior across various datasets and scenarios. -
  Introduced CLI options for accessing private test datasets with authentication tokens. - Enhanced
  dataset download functionality with retry logic and improved authentication handling.

- **Bug Fixes** - Improved handling of DICOM tag reading for non-standard files in unit tests. -
  Refined error handling and context management in NIFTI image writing.

- **Refactor** - Migrated global test configuration to pytest fixtures for better modularity. -
  Updated class and fixture names for clarity in unit tests. - Streamlined internal logic for
  dataset asset processing and progress reporting.

- **Chores** - Removed deprecated and legacy test files to clean up the codebase. - Excluded
  specific code blocks from coverage measurement for more accurate reporting.

- **Style** - Improved code readability and formatting in test files and function signatures.


## v2.0.0-rc.27 (2025-04-28)

### Bug Fixes

- Update CI-CD workflow for PyPI publishing and adjust Python version matrix
  ([`fecdfcd`](https://github.com/bhklab/med-imagetools/commit/fecdfcdc04166ec467d192d7cc625d458fa9f62e))


## v2.0.0-rc.26 (2025-04-28)

### Features

- Add Docker publish workflow to CI-CD process
  ([`ad0d321`](https://github.com/bhklab/med-imagetools/commit/ad0d321d7afb3bfde0e857cc039c76d856515720))


## v2.0.0-rc.25 (2025-04-28)

### Bug Fixes

- Update dependencies for optional groups
  ([`751ea82`](https://github.com/bhklab/med-imagetools/commit/751ea829395ba2aa60cf8598b9cbec440a282602))

### Chores

- Remove unnecessary event type from Docker publish workflow
  ([`81b7b1d`](https://github.com/bhklab/med-imagetools/commit/81b7b1d8af10524f1503f237fd2e7dc964a792f3))

### Refactoring

- Reorganize Dockerfile structure for clarity and maintainability
  ([`e3811b8`](https://github.com/bhklab/med-imagetools/commit/e3811b8a198ccd792e09ed4bc2c77197982098a1))


## v2.0.0-rc.24 (2025-04-28)

### Documentation

- **interlacer**: Enhance documentation for Interlacer module and add error handling classes
  ([`f31d17d`](https://github.com/bhklab/med-imagetools/commit/f31d17d560b1e8d58863ebd7a4b46dc150956735))

### Features

- Autopipeline and Docker Containers
  ([`6ee5a68`](https://github.com/bhklab/med-imagetools/commit/6ee5a68f927a9c34d3e8babbcff97246af3b4095))

### Refactoring

- Add wrapper for extract_metadata to improve parallel processing
  ([`5e8ee49`](https://github.com/bhklab/med-imagetools/commit/5e8ee493be02c6b8a3d76c0a1d13b7dd48066c3f))

- Coretype, logging, transforms ([#338](https://github.com/bhklab/med-imagetools/pull/338),
  [`d029ce9`](https://github.com/bhklab/med-imagetools/commit/d029ce96f7ac1cfa0b2a34f4c840648b89aa1711))

Standardize core types for medical images and enhance logging practices. Update image handling
  methods and improve ROI matching functionality.

- Disable locals in RichTracebackFormatter for cleaner exception logging
  ([`96b71fd`](https://github.com/bhklab/med-imagetools/commit/96b71fd25e1c1ca0d2712f1a095449267cd20d01))

- Enhance error handling and streamline crawling functionality
  ([#337](https://github.com/bhklab/med-imagetools/pull/337),
  [`5e152e0`](https://github.com/bhklab/med-imagetools/commit/5e152e0857a5b278a0e32f46cb50ca2bf4b6944a))

Improve error handling across various components and add unit tests for image utility functions

This update also includes custom exceptions for better error management.

- Enhance ROIMaskMapping to include image_id for better mask handling
  ([`df0a087`](https://github.com/bhklab/med-imagetools/commit/df0a0871b5f3edac6865a06e2394d5ef2acca50a))

- Interlacer qol improvements, and detailed errors
  ([#333](https://github.com/bhklab/med-imagetools/pull/333),
  [`290a848`](https://github.com/bhklab/med-imagetools/commit/290a848c127c37f5b7e2c8d697de6424c5cfb45f))

- **Improvements** - Enhanced readability of displayed identifiers by truncating long values in
  relevant outputs. - Updated terminology in some user-facing messages for greater clarity. - Minor
  formatting improvements in printed output for better presentation. - Improved querying of DICOM
  series with detailed error messages for unsupported or missing modalities. - Added option to group
  query results by root series for clearer organization. - **Tests** - Added comprehensive tests for
  querying and visualizing DICOM data collections, covering both private and public datasets.

Co-authored-by: Jermiah Joseph <44614774+jjjermiah@users.noreply.github.com>

Co-authored-by: Jermiah Joseph <jermiahjoseph98@gmail.com>

- Remove redundant debug logging in NIFTIWriter
  ([`526747e`](https://github.com/bhklab/med-imagetools/commit/526747e958b4afc10be3acc19edafb80cd6e3c46))

- Remove unused __init__.py file from loaders directory
  ([`eb4429b`](https://github.com/bhklab/med-imagetools/commit/eb4429b4aa48d6a8fdd6622fce1a6571438bcbc9))

- Update Python version constraint and add types-pyyaml dependency
  ([`fabd737`](https://github.com/bhklab/med-imagetools/commit/fabd737d217cf5537d8f94a280f5660f62cab08e))


## v2.0.0-rc.23 (2025-04-17)

### Features

- Simplify and update crawler instantiation
  ([#335](https://github.com/bhklab/med-imagetools/pull/335),
  [`f30ec6c`](https://github.com/bhklab/med-imagetools/commit/f30ec6c2159cdec59afd1016198b60d3e2d19280))

Simplify the Crawler class by removing unused settings and references. Update coverage configuration
  to exclude a specific file that causes delays in CI. Clean up references to crawler settings
  throughout the codebase.

- **New Features** - Added access to raw series metadata in DICOM directory parsing results. -
  Expanded the interface of the DICOM crawler to expose additional crawl result components.

- **Refactor** - Simplified the DICOM crawler by consolidating configuration into a single class and
  removing the separate settings object. - Streamlined command-line and internal usage by removing
  support for custom DICOM file extensions and updating initialization patterns.

- **Chores** - Updated test coverage configuration to exclude slow-running sample image generation
  files. - Commented out time-consuming sample image tests to improve CI performance.


## v2.0.0-rc.22 (2025-04-16)

### Features

- Add Mask and VectorMask data structure design proposal with examples and context
  ([#322](https://github.com/bhklab/med-imagetools/pull/322),
  [`2586bce`](https://github.com/bhklab/med-imagetools/commit/2586bcec0c330cbd651af4fbd791559e046f61cc))

- **New Features** - Enhanced segmentation management with new frameworks for both scalar and
  multi-label imaging. - Introduced flexible, strategy-based extraction and mapping of regions of
  interest. - Added robust support for radiological structure set and DICOM segmentation data
  integration, improving ROI extraction and processing. - Implemented comprehensive error handling
  and performance optimizations for smoother operations. - Added methods for creating and managing
  masks from DICOM and numpy data, including vector masks with embedded metadata. - Introduced new
  classes for managing masks and regions of interest, enhancing data structure capabilities. - Added
  a testing framework to validate the initialization and functionality of the new classes. -
  Provided a standalone script to convert and save segmentation and RT structure data as NIFTI files
  with metadata.

Co-authored-by: Joshua Siraj <joshua.siraj@ryerson.ca>

- Add Transform Classes and 3D Visualization tools
  ([#330](https://github.com/bhklab/med-imagetools/pull/330),
  [`366e108`](https://github.com/bhklab/med-imagetools/commit/366e1084284da0c36397bf40340dfefa87d5dfcb))

New Tranform classes introduced, with interfaces to allow for chained tranformations

Added prototypes for vizualizing images during development

- **New Features** - Introduced comprehensive visualization modules for 3D medical images, including
  interactive slice viewers, synchronized multi-image displays, and customizable mask overlays. -
  Added utilities for exporting image slices as GIF and PNG files. - Enabled automatic detection of
  Python runtime environments to enhance user experience. - Provided a suite of synthetic 3D image
  generators for testing and demonstration purposes. - Implemented a unified image transformation
  framework with spatial, intensity, and lambda-based transforms supporting resampling, resizing,
  rotation, cropping, and intensity windowing. - Added a Transformer class to apply sequences of
  image transforms consistently across imaging data types.

- **Bug Fixes** - Ensured robust error handling and validation in transformation pipelines and image
  generation utilities.

- **Documentation** - Included detailed usage examples and comprehensive docstrings across new
  modules. - Added extensive tests validating synthetic image generation and transformation
  correctness.


## v2.0.0-rc.21 (2025-04-15)

### Features

- Implement IndexWriter to support schema evolution
  ([#327](https://github.com/bhklab/med-imagetools/pull/327),
  [`5fcffeb`](https://github.com/bhklab/med-imagetools/commit/5fcffeb79291601b00599ca3bd418ffb305caf09))

Enhance indexing and error handling in AbstractBaseWriter by integrating IndexWriter. Update
  filename formatting to use saved_time, ensure consistency in shared_writer paths, and add a main
  script for ExampleWriter with multiprocessing support. Remove the HDF5Writer class and update
  documentation for clarity.

should address #324

- **New Features** - Introduced a standalone script demonstrating concurrent file writing with
  progress tracking and structured output organization. - Added a robust, concurrent-safe CSV index
  writer with schema evolution support and detailed error handling.

- **Bug Fixes** - Improved filename sanitization to handle whitespace and special characters.

- **Documentation** - Expanded and clarified docstrings for several classes and methods, including
  detailed usage notes and attribute descriptions.

- **Refactor** - Centralized index file management and error handling for file writers. 	- Updated
  logging messages for improved clarity. 	- Simplified field declarations and removed deprecated
  methods.

- **Chores** 	- Removed unimplemented HDF5 writer. 	- Updated test filename format placeholders and
  removed obsolete tests.

### Refactoring

- Handling of metadata, convert datetime where possible
  ([#326](https://github.com/bhklab/med-imagetools/pull/326),
  [`9c212b8`](https://github.com/bhklab/med-imagetools/commit/9c212b8985fda9a57050b675919b2d5d5e95d39a))

- **New Features** - Added support for broader metadata types in scans, allowing metadata values of
  any type. - Introduced automatic conversion of DICOM metadata date, time, and duration fields to
  native Python types. - Added a new test fixture to group medical image test data by collection. 	-
  Implemented new tests to validate scan reading and metadata handling.

- **Bug Fixes** - Improved validation and normalization of DICOM metadata to ensure consistent data
  formats.

- **Documentation** - Enhanced docstrings for new utility functions, including usage examples.

- Refactor + rearrange coretypes module, clean up tests
  ([#321](https://github.com/bhklab/med-imagetools/pull/321),
  [`1f46a55`](https://github.com/bhklab/med-imagetools/commit/1f46a550a4f00a1133f8f933de3700c93192b4e0))

Optimize the import structure, update method signatures, and rename key components for clarity.
  Introduce tests for the ROIMatcher and ensure proper handling of ROI matching strategies.
  Deprecate outdated elements and improve the organization of core types.

- **New Features** - Introduced a structured ROI matching method that returns results in a clear,
  consistent format. - Added an immutable 3D image geometry representation to enhance image
  conversion outputs.

- **Refactor** - Streamlined the image conversion process to always return both image data and
  geometry details. - Standardized naming conventions for ROI matching strategies to improve overall
  clarity.

- **Documentation** - Revised documentation to reflect the updated ROI strategy terminology and
  usage.


## v2.0.0-rc.20 (2025-04-11)

### Bug Fixes

- Sitk 2.4 DICOM reading issue direction handling
  ([#317](https://github.com/bhklab/med-imagetools/pull/317),
  [`519c8d0`](https://github.com/bhklab/med-imagetools/commit/519c8d03443aa929097c8d1becd0a79134530eaf))

Address issues with negative 'SpacingBetweenSlices' in DICOM files by correcting direction cosines.
  Include tests to validate the fix.

Fixes #296

Caused by [Change in GDCM's
  MediaStorageAndFileFormat/gdcmImageHelper.cxx](https://github.com/InsightSoftwareConsortium/ITK/blob/72f509f357570d0e650029b855fb5dee3ded42ee/Modules/ThirdParty/GDCM/src/gdcm/Source/MediaStorageAndFileFormat/gdcmImageHelper.cxx#L1377-L1384)

Reference Issues: https://github.com/SimpleITK/SimpleITK/issues/2214
  https://github.com/InsightSoftwareConsortium/ITK/issues/4794

- update reading classes to also add the metadata

- **New Features** - Enhanced reading capabilities for dose, PET, and scan data with support for
  additional parameters and richer metadata extraction. - Introduced automatic correction of scan
  image direction for improved data accuracy.

- **Documentation** - Updated parameter descriptions and inline guidance to clarify functionality.

- **Tests** - Added new test cases to validate scan direction correction and metadata extraction. -
  Refined test fixtures for improved organization and type safety.


## v2.0.0-rc.19 (2025-04-10)

### Features

- Add ROI matching strategies ([#315](https://github.com/bhklab/med-imagetools/pull/315),
  [`ab9ab3f`](https://github.com/bhklab/med-imagetools/commit/ab9ab3f94012795c26d6157dd319346dbb16ce99))

Update the ruff configuration to ignore specific notebook files and introduce new ROI matching
  strategies with the ROIMatcher class, enhancing the handling of ROI patterns.

- **New Features** - Enhanced support for Jupyter Notebook files by adjusting code analysis checks.
  - Introduced the `ROIMatcher` class for flexible handling of Regions of Interest, allowing various
  input formats and matching strategies. - Defined new ROI handling strategies: `MERGE`,
  `KEEP_FIRST`, and `SEPARATE`.

- **Tests** - Added comprehensive tests to ensure the robust performance of the new Regions of
  Interest matching strategies.


## v2.0.0-rc.18 (2025-04-09)

### Features

- Implement lazy loading in cli click commands
  ([#313](https://github.com/bhklab/med-imagetools/pull/313),
  [`804b407`](https://github.com/bhklab/med-imagetools/commit/804b40736a982fb6d7a9609d2a94a68cb2021481))

- **New Features** - Enhanced CLI experience with organized command groups, making the help output
  clearer and easier to navigate. - Updated DICOM sorting command now provides explicit action
  options (move, copy, symlink, hardlink), improving usability.

- **Bug Fixes** - Improved handling of test datasets with dynamic visibility based on availability.

- **Refactor** - Streamlined handling of test datasets with improved messaging when dependencies are
  missing. - Optimized dependency management and import scoping to ensure a more robust operational
  flow.


## v2.0.0-rc.17 (2025-04-08)

### Features

- Implement MedImage and Scan classes with geometry handling
  ([#303](https://github.com/bhklab/med-imagetools/pull/303),
  [`1888c8a`](https://github.com/bhklab/med-imagetools/commit/1888c8a95a603da685ce13c6c1774f4443a9a888))

Introduce the MedImage class to manage 3D image geometry properties and methods, along with the Scan
  class for metadata handling. This enhances the framework's capability to work with medical images
  effectively.

#277

- **New Features** - Introduced new imaging capabilities, including enhanced support for medical
  scans, dose images, and PET imaging from DICOM data. - Added utilities to extract image metadata
  and convert images to numerical arrays.

- **Refactor** - Streamlined the display format for directional data to a more compact, two-decimal
  representation for improved clarity.

- **Tests** - Updated tests to align with the new directional formatting.

- **Chores** - Deprecated legacy imaging definitions to simplify the codebase.


## v2.0.0-rc.16 (2025-04-08)

### Features

- New AttrDict class in utils, DICOM datetime parsers
  ([#307](https://github.com/bhklab/med-imagetools/pull/307),
  [`8b83b9e`](https://github.com/bhklab/med-imagetools/commit/8b83b9eb157c65a0621ebbf25339bd106a96c6c3))

- **New Features** - Improved the CLI's concurrency option by dynamically setting the default based
  on system capabilities. - Added advanced date & time parsing with ISO formatting for more robust
  handling of imaging data. - Introduced versatile dictionary utilities that enable intuitive nested
  data management. - Streamlined imaging metadata extraction to deliver more relevant outputs.

- **Chores** - Standardized configuration formatting and updated ignore rules for enhanced
  consistency.

- **Tests** - Expanded test coverage to validate the new date/time parsing and dictionary utility
  features.


## v2.0.0-rc.15 (2025-04-07)

### Chores

- Update lockfile
  ([`6efe08d`](https://github.com/bhklab/med-imagetools/commit/6efe08d2c1b2f16f1236d366a958b28a61fec777))

### Features

- **dicom_metadata**: Add additional date and time fields to ModalityMetadataExtractor
  ([#304](https://github.com/bhklab/med-imagetools/pull/304),
  [`5ba35c1`](https://github.com/bhklab/med-imagetools/commit/5ba35c1550ebef168cfaba639481b72a98de7a43))

Enhance the ModalityMetadataExtractor by including extra date and time fields for improved metadata
  extraction.

``` # Date Time Information "StudyDate", "StudyTime", "SeriesDate", "SeriesTime", "ContentDate",
  "ContentTime", "AcquisitionDateTime", "AcquisitionDate", "AcquisitionTime",
  "InstanceCreationDate", "InstanceCreationTime", ```

- **New Features** - Enhanced DICOM metadata extraction to include additional date and time details
  for studies, series, and image content. - Updated the extraction process to now capture instance
  creation information, offering more precise metadata over previous protocol details.

### Refactoring

- **dicom_find**: Improve logging and enhance case-insensitive extension handling
  ([`8f06d24`](https://github.com/bhklab/med-imagetools/commit/8f06d2413efc45c7e435d42da89a33897cdd4121))

### Testing

- **coretypes**: Add more tests for coretypes and direction
  ([#302](https://github.com/bhklab/med-imagetools/pull/302),
  [`01df60c`](https://github.com/bhklab/med-imagetools/commit/01df60c031de3344a387dba1078fde3e5dba9dc3))

Enhance tests for the Direction class and ensure proper initialization and error handling. Update
  the lockfile to reflect dependency changes.

- **Documentation** - Enhanced user guidance by clarifying how to work with orientation matrices and
  spatial data.

- **Bug Fixes** - Improved input validations with descriptive error messages for 3D configuration to
  help prevent misconfiguration.

- **Tests** - Expanded automated checks to verify correct matrix conversions, normalization
  behaviors, and error handling in spatial data utilities.


## v2.0.0-rc.14 (2025-04-07)

### Features

- **cli**: Add index command and update DICOM crawling and parsing
  ([#301](https://github.com/bhklab/med-imagetools/pull/301),
  [`5a179ae`](https://github.com/bhklab/med-imagetools/commit/5a179aebe047a6446f5595343f1819c015b7a2b9))

- Implemented `Crawler` and `CrawlerSettings`

extra: - fixed some things across the testing suite for better output and logging

- **New Features** - Introduced a new CLI indexing command with enhanced options for processing
  DICOM files, including configurable output and parallel processing. - Expanded metadata extraction
  to support additional DICOM tags for richer data capture. - Improved file discovery with smarter
  default extensions and customizable case sensitivity.

- **Refactor** - Streamlined CLI command registration and parameter naming for consistency. -
  Upgraded logging controls to reduce debug noise during operations.

- **Tests** - Added fixtures to suppress debug logging for cleaner test outputs. - Updated test
  parameters for improved validation of image processing and file writing functionalities.


## v2.0.0-rc.13 (2025-04-04)

### Continuous Integration

- Mypy errors and gha for mypy ([#298](https://github.com/bhklab/med-imagetools/pull/298),
  [`90fee16`](https://github.com/bhklab/med-imagetools/commit/90fee166d163d5e1150683e5a320d0f54b5a78ae))

### Features

- Introduce DICOM metadata extraction framework for dicom parsing
  ([#299](https://github.com/bhklab/med-imagetools/pull/299),
  [`ab4fec2`](https://github.com/bhklab/med-imagetools/commit/ab4fec2acfd0f67b2b0486f912d495dc4d4fad8f))

Implement a modality-based metadata extraction framework for DICOM files, improving type handling
  and adding utilities for CT, MR, and PT modalities. Update documentation and tests to ensure
  robustness and clarity.

- **New Features** - Introduced a new command‐line tool to extract metadata from DICOM files. -
  Expanded support for multiple imaging modalities, including CT, MR, PT, segmentation, structured
  reports, and radiotherapy data.

- **Refactor** - Consolidated legacy metadata extraction processes into a modern, modular framework
  for improved reliability. - Streamlined internal data handling and diagnostics.

- **Tests** - Added new tests to validate enhanced metadata extraction and import functionality.


## v2.0.0-rc.12 (2025-04-04)

### Features

- Rebuild pytest configuration and dataset downloading with logging improvements
  ([#294](https://github.com/bhklab/med-imagetools/pull/294),
  [`9fbae4a`](https://github.com/bhklab/med-imagetools/commit/9fbae4a9854527700a531450dd8bcc59a993c6b2))

Update pytest configuration to include new dependencies and improve logging during dataset
  downloads. Enhance test cases to handle timeouts and private repository access more effectively.

- **New Features** - Enhanced logging that now provides clear real-time feedback and improved error
  reporting during dataset operations. - Upgraded asynchronous handling for more robust and
  efficient dataset management.

- **Bug Fixes** - Improved error handling during dataset downloads and metadata validation.

- **Tests** - Streamlined test setup and data management to ensure a smoother testing experience. -
  Integrated new test scenarios to simulate timeouts and secure access, improving overall
  reliability. - Added a new test function to validate metadata associated with medical image test
  data. - Updated minimum release version for compatibility with the latest features.

### Refactoring

- Delete pipeline.py ([#297](https://github.com/bhklab/med-imagetools/pull/297),
  [`54f0a76`](https://github.com/bhklab/med-imagetools/commit/54f0a76b2bf5908623ed6f7b29f136d52e562465))


## v2.0.0-rc.11 (2025-04-04)

### Features

- Enhance testdata downloader with better cli and ability to download private data
  ([#293](https://github.com/bhklab/med-imagetools/pull/293),
  [`2120fb4`](https://github.com/bhklab/med-imagetools/commit/2120fb4f4d690f275769ab69a803a2fdc4181b70))

- Introduce a new `--list-assets` option to the testdata command for listing available assets. - Add
  shorthand options for destination and list-assets to enhance usability. - Improve logging for
  better tracking of available assets.

- **New Features** - Enhanced the command-line experience by adding a new flag to list available
  assets and a more intuitive destination option with clear guidance. - Upgraded asset download
  functionality with improved progress tracking, status reporting, and user-friendly asset
  identification, ensuring smoother operations and clearer user feedback. - Introduced a structured
  approach for managing and downloading datasets from GitHub releases, including robust error
  handling and user feedback.

- **Bug Fixes** - Improved error handling for missing destination directories and asset download
  failures.

- **Chores** - Updated linting configuration to streamline the process by excluding certain files
  and directories.


## v2.0.0-rc.10 (2025-03-28)

### Features

- Enhance CLI organization with groups, add shell-completion
  ([#287](https://github.com/bhklab/med-imagetools/pull/287),
  [`6175600`](https://github.com/bhklab/med-imagetools/commit/6175600da9d9a0050ec378f1a47794a21bdb09e7))

Implement a `SectionedGroup` for better organization of CLI commands and add documentation for shell
  completion in the `imgtools` CLI.

<details><summary>screenshots</summary> <p>

![image](https://github.com/user-attachments/assets/589733c5-1d78-4164-a72d-a60f47da0c1c)

![image](https://github.com/user-attachments/assets/aa516430-3a3d-4335-884a-f241dfaf53dc)

![image](https://github.com/user-attachments/assets/8c99df8c-e204-407a-b2b7-7741d2c2f52a)

</p> </details>

- **New Features** - Launched an organized command-line interface for med-imagetools. - Introduced a
  “dicom-tools” group with commands to find and sort DICOM images, along with an optional testing
  group. - Added a hidden command to generate shell completion scripts for bash, zsh, and fish.

- **Refactor** - Streamlined the command grouping and help output for a clearer and more extensible
  user experience.


## v2.0.0-rc.9 (2025-03-28)

### Chores

- Cleanup deprecated modules and tests ([#280](https://github.com/bhklab/med-imagetools/pull/280),
  [`da8637b`](https://github.com/bhklab/med-imagetools/commit/da8637b3e36ffa88a4b1be85e0a2589dc9029d26))

we will add back files as needed, including testing

<!-- This is an auto-generated comment: release notes by coderabbit.ai --> ## Summary by CodeRabbit

- **Refactor** - Deprecated processing workflows and legacy components have been removed to
  streamline the image processing pipeline and improve overall stability. - Outdated API functions
  and interfaces were retired, paving the way for a more consistent and maintainable system.

- **Chores** - Configuration settings were tightened to enforce stricter quality checks. - Obsolete
  documentation and redundant integrations were cleaned up to simplify future updates and enhance
  reliability. <!-- end of auto-generated comment: release notes by coderabbit.ai -->

- Update utils ([#281](https://github.com/bhklab/med-imagetools/pull/281),
  [`eafa6d0`](https://github.com/bhklab/med-imagetools/commit/eafa6d09f4464b002929e4c317fc1d418cdba8eb))

<!-- This is an auto-generated comment: release notes by coderabbit.ai -->

## Summary by CodeRabbit

- **Refactor** - Streamlined the module’s public interface by removing outdated elements and
  reorganizing available functionality. - Enhanced internal structure and documentation for improved
  clarity and maintainability.

<!-- end of auto-generated comment: release notes by coderabbit.ai -->

### Features

- Delete the modules module in favor of new modality classes in the future
  ([#285](https://github.com/bhklab/med-imagetools/pull/285),
  [`2495a63`](https://github.com/bhklab/med-imagetools/commit/2495a636a359d9474df2553844cb04d1f7cb3ace))

Delete unused modules and refactor the timer utility functions for improved clarity and
  maintainability. Ensure proper formatting by adding a newline at the end of the timer_utils.py
  file.

<!-- This is an auto-generated comment: release notes by coderabbit.ai -->

## Summary by CodeRabbit

- **Refactor** - Removed legacy imaging functionalities including data processing, dose management,
  PET scan handling, image scanning, segmentation, sparse mask generation, and structure conversion.

- **Chores** - Updated test coverage settings and streamlined time-tracking utilities by removing
  demonstration code.

<!-- end of auto-generated comment: release notes by coderabbit.ai -->

### Refactoring

- Rename logging module to loggers to circumvent any name conflicts
  ([#286](https://github.com/bhklab/med-imagetools/pull/286),
  [`34e1f56`](https://github.com/bhklab/med-imagetools/commit/34e1f566b8ce19f75b305d6ccd52cfcbffb60892))

Refactor the codebase to replace logging import paths with the new loggers module. Update coverage
  and ruff configurations accordingly.

<!-- This is an auto-generated comment: release notes by coderabbit.ai -->

## Summary by CodeRabbit

- **Chores** - Updated configurations for testing and code quality tools to ensure consistency.

- **Refactor** - Streamlined internal logging references to align with new organizational standards
  without affecting functionality.

These behind-the-scenes improvements enhance maintainability and clarity, keeping overall system
  behavior unchanged for end-users.

<!-- end of auto-generated comment: release notes by coderabbit.ai -->

- Reorganize dicom module, keep docs updated. add truncate uid to utils
  ([#284](https://github.com/bhklab/med-imagetools/pull/284),
  [`946c615`](https://github.com/bhklab/med-imagetools/commit/946c61513fdba759b6893f2a59a5a5c49f7b5645))

<!-- This is an auto-generated comment: release notes by coderabbit.ai -->

## Summary by CodeRabbit

- **New Features** - Enhanced DICOM reading with additional options for increased flexibility. -
  Introduced a new UID truncation utility for simplified identifier management.

- **Refactor** - Streamlined module organization by consolidating and updating public interfaces. -
  Removed legacy utilities and outdated loading capabilities to promote maintainability.

<!-- end of auto-generated comment: release notes by coderabbit.ai -->

- Update dicom module for sorting, utils, dicom_find. update tests.
  ([#282](https://github.com/bhklab/med-imagetools/pull/282),
  [`9186656`](https://github.com/bhklab/med-imagetools/commit/9186656b1974e6ba7facc37b68e5504ce307959d))

Enhance DICOM processing by updating modules and CLI commands, allowing customizable UID truncation.
  Streamline ruff configuration for better pattern management and add a new dependency for improved
  functionality.

<!-- This is an auto-generated comment: release notes by coderabbit.ai --> ## Summary by CodeRabbit

- **New Features** - Updated the DICOM file search command for a more intuitive file discovery
  process. - Added a CLI option to customize UID truncation when sorting DICOM files. - Enhanced
  spatial calculations by enabling more flexible arithmetic operations for dimension objects.

- **Refactor** - Streamlined internal configurations and API structures for improved DICOM
  processing reliability. - Reorganized the public API of the DICOM module to focus on essential
  functionalities. <!-- end of auto-generated comment: release notes by coderabbit.ai -->


## v2.0.0-rc.8 (2025-03-03)

### Features

- Add timer decorator and enhance DICOM utilities for reference handling
  ([#237](https://github.com/bhklab/med-imagetools/pull/237),
  [`b05b1bf`](https://github.com/bhklab/med-imagetools/commit/b05b1bf9e64b923148e4dd289b9b5a36414686d9))

Introduce a timer decorator for measuring function execution time and improve the retrieval logic
  for RTDOSE reference UIDs. Additionally, add new utilities for handling modality-specific
  references in DICOM files.

## Summary by CodeRabbit

- **New Features** - Expanded DICOM processing capabilities with enhanced extraction of imaging
  references. - Introduced advanced utilities for performance tracking and logging integration,
  improving progress monitoring.

- **Refactor** - Streamlined internal configuration and code formatting for improved consistency.

- **Documentation** - Updated guidance and examples for optional imports and logging utilities.

- **Tests** - Added tests to verify the new timer functionality and performance measurement.


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


## v1.23.2 (2025-02-07)

### Bug Fixes

- Add function to handle out of bounds coordinates for a RegionBox in an image
  ([#221](https://github.com/bhklab/med-imagetools/pull/221),
  [`155f59a`](https://github.com/bhklab/med-imagetools/commit/155f59aec7f2c625ab7cb4f90b97c203d4450abf))

This works the same way as `_adjust_negative_coordinates`, but requires the image as an addition
  input and modifies the RegionBox object directly.

A message is logged in the debugger if a dimension is adjusted.

I also updated the `crop_image` function to call this before applying the crop.


## v1.23.1 (2025-02-07)

### Bug Fixes

- Handle odd extra dimension values in expand_to_min_size
  ([#220](https://github.com/bhklab/med-imagetools/pull/220),
  [`6eb58ea`](https://github.com/bhklab/med-imagetools/commit/6eb58eab110cabc7655372246870488f42c3daf8))


## v1.23.0 (2025-02-07)

### Features

- Add desired_size to centroid bounding box generation
  ([#219](https://github.com/bhklab/med-imagetools/pull/219),
  [`30a129f`](https://github.com/bhklab/med-imagetools/commit/30a129ff47f94328c870c98681215e7561a7546a))

In old version, bounding box was a single voxel. Now is expanded to at least the minimum dimension
  default.

- **New Features** - Now, users can optionally specify a desired size when generating image bounding
  boxes for enhanced control.

- **Chores** - Updated the software version from 1.21.1 to 1.22.0.


## v1.22.0 (2025-02-07)

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
