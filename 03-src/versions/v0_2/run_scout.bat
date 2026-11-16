@echo off
setlocal
.\.venv\Scripts\python.exe -m agent_factory init-db
.\.venv\Scripts\python.exe -m agent_factory verify-sources
.\.venv\Scripts\python.exe -m agent_factory scout
.\.venv\Scripts\python.exe -m agent_factory report
endlocal
