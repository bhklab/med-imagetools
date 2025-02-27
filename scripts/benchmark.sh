#!/bin/bash

hyperfine \
  --warmup 1 \
  --runs 10 \
  --parameter-list num_cores 1,2,4,16,24,48 \
  --export-csv .imgtools/benchmark.csv \
  --export-json .imgtools/benchmark.json \
  --export-markdown .imgtools/benchmark.md \
  ".pixi/envs/dev/bin/python src/imgtools/crawler/crawl2.py -n {num_cores} --force testdata" \
  ".pixi/envs/dev/bin/imgtools index -j {num_cores} testdata"
  # "echo first test with {num_cores} cores; sleep 0.5" \
  # "echo second test with {num_cores} cores; sleep 0.5"
