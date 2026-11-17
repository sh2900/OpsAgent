
@echo off
setlocal
cd /d "%~dp0"

echo ========================================
echo          OpsAgent Setup
echo ========================================

echo.
echo Checking Python...
set "PY_CMD=python"
python --version >nul 2>&1
if errorlevel 1 (
    py -3 --version >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=py -3"
    ) else (
        goto python_error
    )
)

%PY_CMD% --version

%PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)"
if errorlevel 1 goto python_version_error

echo.
echo Creating virtual environment...
if not exist ".venv\Scripts\python.exe" (
    %PY_CMD% -m venv .venv
)
if errorlevel 1 goto error

echo.
echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto error

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error

echo.
echo Preparing environment configuration...
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo Created .env from template.
    ".venv\Scripts\python.exe" -c "import secrets, pathlib; p = pathlib.Path('.env'); c = p.read_text(); c = c.replace('GENERATE_YOUR_OWN_SECRET', secrets.token_urlsafe(32)).replace('CHANGE_THIS_TO_A_STRONG_PASSWORD', 'admin_password_123'); p.write_text(c)"
    echo Automatically generated JWT Secret Key and set default Admin Password (admin_password_123).
) else (
    echo Existing .env preserved.
)

echo.
echo Reading LLM configuration...
set "LLM_PROVIDER="
set "LLM_MODEL="

for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    if /I "%%A"=="LLM_PROVIDER" set "LLM_PROVIDER=%%B"
    if /I "%%A"=="LLM_MODEL" set "LLM_MODEL=%%B"
)

if /I not "%LLM_PROVIDER%"=="ollama" goto model_done

echo.
echo Ollama provider selected.

where ollama >nul 2>&1
if errorlevel 1 goto ollama_missing

echo Downloading %LLM_MODEL%...
ollama pull "%LLM_MODEL%"
if errorlevel 1 goto model_pull_warning

goto model_done

:ollama_missing
echo WARNING: Ollama is not installed.
echo Install Ollama before running OpsAgent.
goto model_done

:model_pull_warning
echo WARNING: Model download failed.
echo You can run ollama pull %LLM_MODEL% manually.
goto model_done

:model_done

echo.
echo ========================================
echo Setup completed!
echo.
echo IMPORTANT:
echo 1. Configure your .env file.
echo 2. Set your MongoDB connection.
echo 3. Generate your own JWT secret.
echo 4. Set your own administrator credentials.
echo 5. Ensure your selected LLM provider is available.
echo.
echo Run start.bat to launch OpsAgent.
echo ========================================
pause
exit /b 0

:python_error
echo ERROR: Python is not installed or not in PATH.
pause
exit /b 1

:python_version_error
echo ERROR: Python 3.10 or newer is required.
pause
exit /b 1

:error
echo.
echo SETUP FAILED. Check the error above.
pause
exit /b 1
