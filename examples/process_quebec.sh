#!/usr/bin/env bash
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
TOP_DIR="$(dirname "$SCRIPT_DIR")"

python $TOP_DIR/imgtools/autopipeline.py\
     $SCRIPT_DIR/data/tcia_samples/Head-Neck-PET-CT \
     $SCRIPT_DIR/data/tcia_nrrd \
     --modalities CT,RTSTRUCT \
     --n_jobs 1