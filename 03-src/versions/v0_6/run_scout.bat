@echo off
python -m agent_factory init-db
python -m agent_factory verify-sources
python -m agent_factory scout
python -m agent_factory report
pause
