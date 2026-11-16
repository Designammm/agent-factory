# Agent Factory v0.1

Local-first scout/factory for discovering AI agents that appear to earn money,
extracting public operating patterns, scoring reproducibility, and producing
implementation blueprints.

v0.1 only researches public data. It does not bid, spend money, access wallets,
or store private credentials.

Windows:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m agent_factory scout
.\.venv\Scripts\python.exe -m agent_factory report
```
