#!/bin/bash

hyperfine \
  --warmup 2 \
  --runs 3 \
  --parameter-list num_cores 1,4,8,12,24,36,48 \
  --export-csv .imgtools/benchmark.csv \
  --export-json .imgtools/benchmark.json \
  --export-markdown .imgtools/benchmark.md \
  --command-name "CompareCrawl" \
  ".pixi/envs/dev/bin/python src/imgtools/crawler/crawl2.py -n {num_cores} --force data" \
  ".pixi/envs/dev/bin/imgtools index -j {num_cores} data"
