@echo off
rem Runs Wayfarer from source using the project's virtual environment.
cd /d "%~dp0"
venv\Scripts\python.exe -m wayfarer
if errorlevel 1 pause
