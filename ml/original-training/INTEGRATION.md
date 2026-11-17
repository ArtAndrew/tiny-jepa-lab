# Preserved recovered training package

The 17 numerical source/test/export files listed in `reference/ORIGINAL_SOURCE_SHA256.json` are unchanged. `reference/` contains supplied historical records and an externally performed Linux reproduction; these are not the new local measurements.

Recommended entry point from the repository root:

```sh
python -m planning.original_training --out runs/original-42 --ablation
```

The wrapper copies this source into an empty workspace, trains every component from random initialization, runs the original checks and exports a complete model bundle. It never loads `artifacts/original-training/`. The root site's builder and leaderboard continue to use their existing model.

[Full instructions and new measured evidence](../../FROM_SCRATCH.md). The notebooks and website inside this preserved package are historical supplementary files; use the current [from-scratch notebook](../../materials/ORBIT_From_Scratch.ipynb) for the integrated workflow.
