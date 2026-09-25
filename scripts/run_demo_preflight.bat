@echo off
setlocal EnableExtensions

set "REPO_ROOT=%~1"
if "%REPO_ROOT%"=="" set "REPO_ROOT=F:\trialiq"
set "BASE_URL=%~2"
if "%BASE_URL%"=="" set "BASE_URL=http://127.0.0.1:8000"

set "PYTHON=%REPO_ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"

if not exist "%REPO_ROOT%\scripts\demo_preflight.py" (
  echo [ERROR] TrialIQ demo preflight script was not found under "%REPO_ROOT%\scripts".
  exit /b 2
)

"%PYTHON%" "%REPO_ROOT%\scripts\demo_preflight.py" --base-url "%BASE_URL%"
exit /b %ERRORLEVEL%
