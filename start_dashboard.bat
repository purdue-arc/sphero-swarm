@echo off
cd /d "%~dp0"
if exist ".venv\" (
    uv run --no-sync python coordinator\server.py
) else (
    uv run python coordinator\server.py
)
pause
