#!/bin/bash
/Users/shahr2/mambaforge/envs/kreview-eval/bin/kreview run \
  --cancer-samplesheet "/Users/shahr2/Library/Group Containers/G69SCX94XU.duck/Library/Application Support/duck/Volumes.noindex/shahr2 - islogin01.mskcc.org – SFTP/share/krewlyzer/0.8.2/access_12_245/samplesheet.csv" \
  --healthy-xs1-samplesheet "/Users/shahr2/Library/Group Containers/G69SCX94XU.duck/Library/Application Support/duck/Volumes.noindex/shahr2 - islogin01.mskcc.org – SFTP/share/krewlyzer/0.8.2/healthy_controls/xs1/samplesheet.csv" \
  --healthy-xs2-samplesheet "/Users/shahr2/Library/Group Containers/G69SCX94XU.duck/Library/Application Support/duck/Volumes.noindex/shahr2 - islogin01.mskcc.org – SFTP/share/krewlyzer/0.8.2/healthy_controls/xs2/samplesheet.csv" \
  --cbioportal-dir "/Users/shahr2/Documents/Github/msk-impact/msk_solid_heme" \
  --krewlyzer-dir "manifest.txt" \
  --output output/ \
  --workers 4 \
  --export-duckdb \
  --chunk-size 50
