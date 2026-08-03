# AGENTS.md

## Cursor Cloud specific instructions

`med-imagetools` is a single Python package that ships the `imgtools` command-line
application for turning messy DICOM datasets into deep-learning-ready formats. There is
no GUI or long-running server: it is a CLI plus a test/lint/docs toolchain, all managed
by [`pixi`](https://pixi.sh) (see `pixi.toml`).

### Environment / running commands

- The project is driven by `pixi`. The startup update script installs the `dev`
  environment (`pixi install -e dev`). Prefix commands with `pixi run -e <env> ...`.
- `pixi` is installed at `~/.pixi/bin` and added to `PATH` via `~/.bashrc`. In a
  non-interactive shell where `~/.bashrc` is not sourced, either call it as
  `~/.pixi/bin/pixi` or add `~/.pixi/bin` to `PATH` first.
- Relevant environments (defined in `pixi.toml`): `dev` (everything, incl. the editable
  install with `[all]` extras), `test` (test + quality/lint tools), `docs`.
- The `pixi lock ... v6 vs v7` WARN on every command is harmless; do not "fix" it by
  regenerating the lockfile as part of unrelated work.

### Lint / test / build / run

Standard tasks are defined in `pixi.toml`; prefer them over ad-hoc commands:

- Lint (matches CI): `pixi run -e test ruff-check`, `pixi run -e test ruff-format --diff`,
  `pixi run -e test type-check` (mypy).
- Unit tests: `pixi run -e test unittests` (runs `pytest -m unittests`). ~200 fast tests
  that load no external data.
- Integration tests: `pixi run -e test integration`. These download DICOM test data from
  GitHub releases (public data works without a token; some datasets/tests require a
  GitHub token — see below), so they need network access and are much slower.
- Docs: `pixi run -e docs doc-build` (mkdocs). The many `griffe:` docstring warnings are
  pre-existing and non-fatal.
- Run the app: `pixi run -e dev imgtools --help`. Core subcommands: `index`, `interlacer`,
  `autopipeline`, `nnunet-pipeline`; utilities: `dicomfind`, `dicomsort`, `dicomshow`.

### Test data (non-obvious)

- `imgtools testdata --list-assets` lists downloadable public datasets;
  `imgtools testdata -d <dir> -a <AssetName>` downloads one. This hits the public
  `bhklab/med-image_test-data` GitHub releases.
- Private test data and the full integration matrix need a GitHub token (CI uses
  `MEDIMG_TESTDATA_PAT` / `BHKLAB_GITHUB_TOKEN`); pass it via `imgtools testdata -p -t <token>`.
  Without a token, only public assets/tests are available.
- A quick end-to-end sanity check: download a small dataset and run
  `imgtools index --dicom-dir <downloaded_dir> --dataset-name demo`, which writes
  `index.csv` and JSON crawl outputs into a `.imgtools/` folder next to the DICOM dir.
