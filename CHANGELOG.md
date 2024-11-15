# CHANGELOG


## v1.6.0-rc.2 (2024-11-14)

### Bug Fixes

- Update version_toml path in pyproject.toml for semantic release
  ([`0dacfee`](https://github.com/bhklab/med-imagetools/commit/0dacfee32c75950c104104057a0cef6c6ab536cd))


## v1.6.0-rc.1 (2024-11-14)

### Bug Fixes

- Added linux to pixi
  ([`023a111`](https://github.com/bhklab/med-imagetools/commit/023a111d3bf2b83175d971c02641a786de6b91f9))

- Explicitly direct location of package code and update pixi in pipeline
  ([`6767ced`](https://github.com/bhklab/med-imagetools/commit/6767ced27ed52eb6171243534c1364d91728baf5))

### Build System

- Added coverage to gha
  ([`6382dbf`](https://github.com/bhklab/med-imagetools/commit/6382dbfe0c37a031f9017130464f5895e11c792c))

### Chores

- **sem-ver**: 1.6.0-rc.1
  ([`cff36b9`](https://github.com/bhklab/med-imagetools/commit/cff36b99d2739d761b12c5264d487bbea983628d))

- Update GitHub Actions workflow to deploy from both main and devel branches, and refresh
  dependencies in pixi.lock
  ([`60350d6`](https://github.com/bhklab/med-imagetools/commit/60350d64f287085b2f1489af934702d6ad5e7c15))

- Clean up GitHub Actions workflow by removing commented-out jobs and updating dependencies
  ([`8274e4d`](https://github.com/bhklab/med-imagetools/commit/8274e4d3d36f461c41698174696d902fb8e1fa45))

- Update GitHub Actions workflow for improved deployment process
  ([`ddad006`](https://github.com/bhklab/med-imagetools/commit/ddad0067796ed0b8539e21a0e380e6325853f886))

### Features

- Updated test suite for pixi and started refactor of cicd
  ([`cc94817`](https://github.com/bhklab/med-imagetools/commit/cc9481735c9ea19dc534973d345042a77ebecafb))

- Started port to pixi
  ([`0ff9b90`](https://github.com/bhklab/med-imagetools/commit/0ff9b90f1327fee183025ef40c204168fb9810e2))


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
