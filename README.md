# Agent Factory — cleaned project

## Active source
The active v0.7.0 Python package is in `03-src/agent_factory/`.

## Windows setup
From this project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r 03-src\requirements.txt
$env:PYTHONPATH = "03-src"
python -m pytest -q 05-tests\tests
python -m agent_factory init-db
python -m agent_factory verify-sources
python -m agent_factory scout
python -m agent_factory report
```

The package uses `03-src/config.json` and stores its runtime database and generated
reports under `03-src/data/` and `03-src/reports/`.

## Folder map
- `00-project/` — project definition, requirements and roadmap
- `01-research/` — research and user feedback
- `03-src/` — active source package and runtime configuration
- `05-tests/` — active tests and historical version tests
- `06-reports/` — audit, evaluation and research reports
- `07-docs/` — business plans and specifications
- `99-archive/` — historical version ZIPs and preserved export differences

See `06-reports/cleanup-audit.md` for cleanup decisions and known limitations.
