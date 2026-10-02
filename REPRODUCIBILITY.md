# Reproducibility Guide

## Declared scope

This release reproduces a deterministic in-memory reference model only. It has
no network, filesystem, shell, MCP, provider, database, or real-tool executor.
It does not reproduce a protected engineering system or make a production
safety claim.

## Supported interpreters

- Python 3.9
- Python 3.13

The demo has no third-party runtime dependency. It requires only the Python
standard library and the source tree in this release.

## Source checkout commands

On Windows Command Prompt:

```text
set PYTHONPATH=src
py -3.9 -m unittest discover -s tests -v
py -3.13 -m unittest discover -s tests -v
py -3.13 tools/run_reference_cases.py
py -3.13 tools/run_semantic_ablation.py
py -3.13 -m wbstg.cli examples/valid_transition.json
```

On POSIX shells, replace the first line with `PYTHONPATH=src` before each
command, or install the package with `python -m pip install .`.

## Expected public evidence

- Both interpreter runs report `Ran 14 tests` and `OK`.
- `results/fixed_cases_v0.2.2.json` reports 7/7 declared decision and
  observation agreement plus 1/1 replay verification.
- `results/semantic_ablation_v0.2.2.json` reports four intentionally reduced
  semantic baselines; it is not a comparison with an external product.
- `SHA256SUMS.txt` and `RELEASE_MANIFEST.json` bind the release contents.

## Integrity procedure

Before using the release, verify every listed hash with a SHA-256 utility. A
matching internal manifest detects accidental or partial modification. Obtain
the Git tag or release checksum through an independent trusted channel if you
need assurance that the entire package was not replaced together with its
manifest.
