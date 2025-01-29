# Testing Information

Med-imagetools uses the `pytest` framework with `pixi`
to assist with testing, and `coverage` to measure test coverage.

Mainly, being able to run a test suite across a matrix of
python environments in CI/CD automatically.

See the `test` feature in the `pixi.toml` file for the
dependencies, and tasks.

## Data

As of January 2025, the test data is downloaded from the
[`bhklab/med-image_test-data`](https://github.com/bhklab/med-image_test-data)
which is an automated pipeline that uses `snakemake` to query,
download and prepare the data. The pipeline is run on
GitHub Actions, and the data is uploaded to the `releases`
section of the repository where it is then sourced by
many packages.

Med-Imagetools has an interface in `src/imgtools/datasets` that
can be used to download the data, and prepare it for testing.
If users want to use the data, they need to install the package with
`med-imagetools[test]` so it has the dependencies to download the data.

our `pixi` configuration includes the optional-dependencies for the entire
package so we dont have to worry much about it.

