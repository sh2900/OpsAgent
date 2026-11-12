
@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo          Starting OpsAgent
echo ========================================

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found.
    echo Run setup.bat first.
    pause
    exit /b 1
)

if not exist ".env" (
    echo ERROR: .env file not found.
    echo Configure .env before starting.
    pause
    exit /b 1
)

echo.
echo Checking environment configuration...

findstr /C:"PASTE_YOUR_MONGODB_ATLAS_URI_HERE" .env >nul
if not errorlevel 1 goto config_error

findstr /C:"GENERATE_YOUR_OWN_SECRET" .env >nul
if not errorlevel 1 goto config_error

findstr /C:"CHANGE_THIS_TO_A_STRONG_PASSWORD" .env >nul
if not errorlevel 1 goto config_error

echo Configuration placeholders checked.

echo.
echo Reading LLM configuration...

set "LLM_PROVIDER="
set "LLM_MODEL="

for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /I "%%A"=="LLM_PROVIDER" set "LLM_PROVIDER=%%B"
    if /I "%%A"=="LLM_MODEL" set "LLM_MODEL=%%B"
)

if not defined LLM_PROVIDER goto config_error
if not defined LLM_MODEL goto config_error

if /I not "%LLM_PROVIDER%"=="ollama" goto start_services

echo.
echo Checking Ollama...

where ollama >nul 2>&1
if errorlevel 1 goto ollama_missing

ollama list >nul 2>&1
if errorlevel 1 (
    echo Starting Ollama...
    start "OpsAgent - Ollama" cmd /k "ollama serve"
    timeout /t 8 /nobreak >nul
)

ollama list | findstr /I /C:"%LLM_MODEL%" >nul
if errorlevel 1 (
    echo ERROR: Model %LLM_MODEL% is not installed.
    echo Run: ollama pull %LLM_MODEL%
    pause
    exit /b 1
)

:start_services

echo.
echo Starting simulator...
start "OpsAgent - Simulator" /D "%~dp0" "%~dp0.venv\Scripts\python.exe" -m uvicorn sim_backend.main:sim --reload --port 8001

timeout /t 3 /nobreak >nul

echo Starting FastAPI backend...
start "OpsAgent - FastAPI" /D "%~dp0" "%~dp0.venv\Scripts\python.exe" -m uvicorn backend.main:app --reload --port 8000

timeout /t 3 /nobreak >nul

echo Starting Streamlit dashboard...
start "OpsAgent - Dashboard" /D "%~dp0" "%~dp0.venv\Scripts\python.exe" -m streamlit run dashboard\app.py

echo.
echo ========================================
echo OpsAgent services launched!
echo.
echo Dashboard: http://localhost:8501
echo API Docs:  http://localhost:8000/docs
echo Simulator: http://localhost:8001/docs
echo ========================================
pause
exit /b 0

:config_error
echo ERROR: Your .env configuration is incomplete.
echo Check MongoDB URI, LLM settings, JWT secret and admin credentials.
pause
exit /b 1

:ollama_missing
echo ERROR: Ollama is required for the selected provider.
echo Install Ollama and run setup.bat again.
pause
exit /b 1
