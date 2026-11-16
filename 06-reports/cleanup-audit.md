# Cleanup audit — Agent Factory

## Source archive
- Uploaded archive: `001 Agent Factory(1).zip`
- Entries inspected: 91 files
- Extracted source payload: approximately 1.11 MB

## Canonical active source
- Active source package: `03-src/agent_factory/`
- Runtime configuration: `03-src/config.json`
- Dependencies: `03-src/requirements.txt`
- Windows launcher: `03-src/run_scout.bat`
- Tests: `05-tests/`

The active package was extracted from `99-archive/Agent_Factory_v0_7.zip`.
The package directory inside that archive is named `agent_factory_v0_6`, but its README,
changelog, CLI and audit identify the code as v0.7.0. The extracted core.py is byte-identical
to the existing `03-src/agent/v0_6/core.py`.

## Important finding
No `migrations.py` exists in the supplied project tree or in the v0.7 archive.
The active package contains migration logic inside `agent_factory/core.py`.
No new migration module was fabricated.

## Duplicate handling
- The `_github-agent-factory` nested mirror was not copied as a second active project.
- Exact duplicate mirrored files were collapsed.
- Its unique `.env.example`, alternate `.gitignore`, and alternate test prompt were preserved
  under `99-archive/redundant-export-differences/` (except `.env.example`, also copied to root).
- Byte-identical v0.4.5 ZIP duplicate was collapsed; one copy is retained.
- Historical version ZIP files are retained under `99-archive/`.

## Root policy
Only project-level control files remain at root: `README.md`, `.gitignore`, `.env.example`.
All code, tests, docs, reports, research, assets and historical archives are filed in named folders.

## Validation
The archive extraction and file classification completed. Original ZIP archives were not modified.

## Test execution status
- A fresh test run was attempted with `py -m pytest -q -p no:cacheprovider 05-tests/tests`.
- The only Python interpreter registered on this machine is Python 3.15; it does not have `pytest` installed (`No module named pytest`).
- Therefore, this run did not execute the tests and no new pass/fail result is claimed.
- Install the project's test dependencies, then rerun the command above.

## Archive distribution
- 160 files initially extracted and classified from the v0.1-v0.7 ZIP archives into versioned source, test, report, data and documentation folders.
- 23 byte-identical collisions skipped.
- 0 conflicting files found; no archive payload was overwritten.
- 18 cache/bytecode entries skipped during extraction.
- All original release ZIP files remain in `99-archive/`.
- Active v0.7 source remains in `03-src/agent_factory/`; its archived `core.py` is byte-identical.
- The byte-identical v0.7 source snapshot was collapsed into the active package to avoid a second working copy; the original v0.7 ZIP remains preserved.
- Runtime cache folders (`__pycache__`, `.pytest_cache`) were removed from the project tree.
- Python syntax compilation completed successfully for the active package and active tests (`compileall`, exit code 0).
- Pytest remains unverified on this machine because `pytest` is not installed in its only registered Python interpreter.
