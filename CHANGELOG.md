# CHANGELOG


## v1.9.4 (2024-11-29)

### Bug Fixes

- Update GitHub Actions workflow for concurrency and permissions;
  ([`45cddb4`](https://github.com/bhklab/med-imagetools/commit/45cddb4fd65be0df14a7f9d2a28261c5cc36159b))

- Configure Git credentials for GitHub Actions and update documentation deployment step
  ([`adf4e04`](https://github.com/bhklab/med-imagetools/commit/adf4e0431533d7434780951edd6ec82737cac21e))


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

### Chores

- **sem-ver**: 1.9.3
  ([`d9d1fd0`](https://github.com/bhklab/med-imagetools/commit/d9d1fd0f7d9817ca2c0d4e9d1d5132673b2478c3))


## v1.9.2 (2024-11-22)

### Bug Fixes

- Pipeline entry no longer needs to manually configure loglevel
  ([`66f8119`](https://github.com/bhklab/med-imagetools/commit/66f8119e6e2e1356c1e3b154e7ad2143cb77ea52))

### Chores

- **sem-ver**: 1.9.2
  ([`22d8fb7`](https://github.com/bhklab/med-imagetools/commit/22d8fb77f1d2c47d26967b1578e9be41d829dbb1))

- **deps**: Update med-imagetools to version 1.9.1 and update sha256 checksum
  ([`ab77c58`](https://github.com/bhklab/med-imagetools/commit/ab77c5887e5bb8ae1fa477d2780b94dcdf3297a6))

### Refactoring

- **logging**: Simplify logger configuration and enhance environment variable handling
  ([`c1f624b`](https://github.com/bhklab/med-imagetools/commit/c1f624b7dc14d85176d97bf22918fb2f49dc4a8b))


## v1.9.1 (2024-11-22)

### Bug Fixes

- Downstream bug where datagraph.py was missing from wheel due to data* being ignored in .gitignore
  ([`2dbb245`](https://github.com/bhklab/med-imagetools/commit/2dbb2455e1edcbf663effd8d40b6bff88dc92082))

### Chores

- **sem-ver**: 1.9.1
  ([`711934c`](https://github.com/bhklab/med-imagetools/commit/711934cc211bd53347ad5c46cb873dae441f1796))

### Documentation

- Fix broken images
  ([`a7d0e3a`](https://github.com/bhklab/med-imagetools/commit/a7d0e3a70959e9a754efcade9f9f3aa75206c9ad))


## v1.9.0 (2024-11-22)

### Chores

- **sem-ver**: 1.9.0
  ([`b597892`](https://github.com/bhklab/med-imagetools/commit/b597892041fb5dc096d43a757b3482bb20ba5293))

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

### Chores

- **sem-ver**: 1.8.2
  ([`359cc09`](https://github.com/bhklab/med-imagetools/commit/359cc09a910b00e617157a0474d5b16f44b3253a))


## v1.8.1 (2024-11-21)

### Bug Fixes

- Common prefix for tree
  ([`a940969`](https://github.com/bhklab/med-imagetools/commit/a94096910b3b95629e96e809ec21a705505fe841))

### Chores

- **sem-ver**: 1.8.1
  ([`3e1c40d`](https://github.com/bhklab/med-imagetools/commit/3e1c40d1441e305dc55c3256e0563c3317765299))


## v1.8.0 (2024-11-21)

### Chores

- **sem-ver**: 1.8.0
  ([`f5d97d0`](https://github.com/bhklab/med-imagetools/commit/f5d97d01f45d58d5478e49429be4754f62b3e80c))

### Features

- Add dicomsorting cli entry
  ([`d435f93`](https://github.com/bhklab/med-imagetools/commit/d435f93f0f2fda67094e4aeaa8a1828a570c534d))


## v1.7.0 (2024-11-19)

### Chores

- **sem-ver**: 1.7.0
  ([`d579680`](https://github.com/bhklab/med-imagetools/commit/d579680f37b4f37f299fbe0e69d7dd653ae52000))

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

Co-authored-by: coderabbitai[bot] <136622811+coderabbitai[bot]@users.noreply.github.com>

* chore: update .gitignore to include log files in imgtools directory

* feat(datagraph): integrate logging for edge table processing and visualization

* feat(ops): add timing for graph formation and update DataGraph initialization

* chore: rename workflow from Test to CI-CD and restrict push triggers to main branch

* feat(crawl): integrate logging for folder crawling and data saving processes

* fix(structureset): enhance logging for ROI point retrieval errors

* fix(autopipeline): update logger level to use environment variable for flexibility

* fix(logging): streamline error handling for log directory creation

* fix: https://github.com/bhklab/med-imagetools/pull/134#discussion_r1847278305

Co-authored-by: coderabbitai[bot] <136622811+coderabbitai[bot]@users.noreply.github.com>

* refactor(logging): enhance logging configuration and streamline JSON setup

* chore(pixi.lock): add license_family field for clarity

* refactor(logging): enhance LoggingManager with valid log levels and improve JSON logging setup

* refactor(logging): enhance documentation and improve LoggingManager configuration options

* refactor(logging): validate log level assignment before setting self.level

* feat(logging): add mypy and type-checking support; refactor logging manager and improve error
  handling

* refactor(logging): remove unused Optional import from typing

---------

Co-authored-by: coderabbitai[bot] <136622811+coderabbitai[bot]@users.noreply.github.com>


## v1.6.0 (2024-11-15)

### Chores

- **sem-ver**: 1.6.0
  ([`1549be9`](https://github.com/bhklab/med-imagetools/commit/1549be986f235ec346d7c8cb37d5a582c61d20a7))

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

### Chores

- **sem-ver**: 1.5.8
  ([`84aa480`](https://github.com/bhklab/med-imagetools/commit/84aa48014308784eef4314750da708682cea2968))


## v1.5.7 (2024-10-23)

### Bug Fixes

- Ci-cd - add id in release for pypi step
  ([`7abd175`](https://github.com/bhklab/med-imagetools/commit/7abd175d58894b5ea84448735c4933de4aa156bd))

### Chores

- **sem-ver**: 1.5.7
  ([`c9a10bb`](https://github.com/bhklab/med-imagetools/commit/c9a10bbbfe7cc0e026c6a1719c07361bb7f3187f))


## v1.5.6 (2024-10-23)

### Bug Fixes

- Update ci to release to pypi
  ([`a92a41f`](https://github.com/bhklab/med-imagetools/commit/a92a41f56ab6d86c68d7657104f8c559b1958ffc))

### Chores

- **sem-ver**: 1.5.6
  ([`22881f1`](https://github.com/bhklab/med-imagetools/commit/22881f19cabf0b9a096fe3d1822cd0ed26dcb507))


## v1.5.5 (2024-10-23)

### Bug Fixes

- Update ci to use semver bot
  ([`98e3bd0`](https://github.com/bhklab/med-imagetools/commit/98e3bd0c93fc2be20c31976092047e7a11db57fb))

- Remove deprecated pydicom.dicomdir.DicomDir variable type option
  ([#130](https://github.com/bhklab/med-imagetools/pull/130),
  [`56ef37e`](https://github.com/bhklab/med-imagetools/commit/56ef37e492d9a4f287ed9ecb7a1c968caca29726))

* fix: remove deprecated pydicom.dicomdir.DicomDir variable type option

* style: removed Union since dicom_data can only be a FileDataset

* refactor: remove Union import for linting

### Chores

- **sem-ver**: 1.5.5
  ([`9921fba`](https://github.com/bhklab/med-imagetools/commit/9921fba8c74d5bfb6d914ce7af069df3976acde0))

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

### Chores

- **sem-ver**: 1.5.4
  ([`464462c`](https://github.com/bhklab/med-imagetools/commit/464462cb1718d96652382f115b2f20ae4d8cbee8))


## v1.5.3 (2024-06-10)

### Bug Fixes

- Clarified license in README.md ([#118](https://github.com/bhklab/med-imagetools/pull/118),
  [`a4899ca`](https://github.com/bhklab/med-imagetools/commit/a4899ca15924dc9fa19f2e1f3964b7bd6c2e2d35))

### Chores

- **sem-ver**: 1.5.3
  ([`7effcaf`](https://github.com/bhklab/med-imagetools/commit/7effcaffbe054995bb3111d3799bc8b7d9246300))


## v1.5.2 (2024-05-29)

### Bug Fixes

- Upload latest version to pypi
  ([`1debad3`](https://github.com/bhklab/med-imagetools/commit/1debad3836732faf1a2e3f992a9f1d76943b076e))

### Chores

- **sem-ver**: 1.5.2
  ([`69a651f`](https://github.com/bhklab/med-imagetools/commit/69a651f464b418c92f951be33bb865a04f0c604d))


## v1.5.1 (2024-05-29)

### Bug Fixes

- Format toml
  ([`269f55d`](https://github.com/bhklab/med-imagetools/commit/269f55db58322dc31a5c44ee5a5e2eb830ed3e4f))

### Chores

- **sem-ver**: 1.5.1
  ([`7890f36`](https://github.com/bhklab/med-imagetools/commit/7890f3638e76b449f3948ae3c8c4a9532bde10ae))


## v1.5.0 (2024-05-29)

### Chores

- **sem-ver**: 1.5.0
  ([`69626ef`](https://github.com/bhklab/med-imagetools/commit/69626ef244aa26a8c7d5235548651cf4230e2b9a))

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
