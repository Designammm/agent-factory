# Source Material Inventory

## Status

The contents of `ALL FILES` have been copied into the project architecture without deleting or modifying the originals.

The bilingual project requirements are maintained separately in:
- `00-project/requirements-en.md`
- `00-project/requirements-fa.md`

## Mapping

| Source material | Canonical destination |
|---|---|
| Business plans v1, v2 and v3 | `07-docs/specifications/` |
| AF-CC-S000 feedback PDF | `01-research/user-notes/` |
| v0.7 evaluation report | `06-reports/evals/` |
| Active v0.7 Python package | `03-src/agent_factory/` |
| Active runtime config and dependencies | `03-src/config.json`, `03-src/requirements.txt` |
| Active seed/runtime data | `03-src/data/` |
| Active test suite and v0.7 test prompt | `05-tests/` |
| Historical source and release config v0.1-v0.6 | `03-src/versions/<version>/` |
| Active v0.7 source | `03-src/agent_factory/` (one canonical copy; ZIP retained in archive) |
| Historical tests | `05-tests/version-history/<version>/` |
| Historical reports | `06-reports/reports/version-history/<version>/` |
| Historical seed data | `03-src/data/version-history/<version>/` |
| Historical README, checkpoint and changelog files | `07-docs/specifications/version-history/<version>/` |
| Original release ZIP files | `99-archive/` |
| Non-identical export variants | `99-archive/extracted-differences/` |

## Preservation

Original release ZIP files are retained unchanged in `99-archive/`. Extracted historical files are filed by type and version. The active v0.7 package remains separate from historical snapshots.

## Language separation

The extracted project requirements are available in both languages. Source material remains in its original language; it is not duplicated or machine-translated merely for folder symmetry.
