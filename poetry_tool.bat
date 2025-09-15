@echo off
setlocal EnableDelayedExpansion

:MENU
cls
echo ========================================
echo    Poetry Annotation Tool Manager
echo ========================================
echo.
echo Please choose an option:
echo.
echo 1. Quick Start (Install + Run)
echo 2. Install Dependencies Only
echo 3. Run Application
echo 4. Run Application (Alternative)
echo 5. Clean Cache and Restart
echo 6. Exit
echo.
echo ========================================
set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto QUICK_START
if "%choice%"=="2" goto INSTALL_ONLY
if "%choice%"=="3" goto RUN_APP
if "%choice%"=="4" goto RUN_WITH_VENV
if "%choice%"=="5" goto CLEAN_RESTART
if "%choice%"=="6" goto EXIT
echo Invalid choice. Please try again.
pause
goto MENU

:QUICK_START
cls
echo ========================================
echo Quick Start - Install and Run
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    goto MENU
)

echo Python found: 
python --version
echo.

REM Install dependencies directly to system Python
echo Installing/updating dependencies...
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    goto MENU
)

echo.
echo Setup completed! Starting application...
echo Browser will open at: http://localhost:8501
echo.
echo To stop: Close this window or press Ctrl+C
echo ========================================
echo.

streamlit run app.py
goto END

:INSTALL_ONLY
cls
echo ========================================
echo Install Dependencies Only
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed
    pause
    goto MENU
)

echo Python found: 
python --version
echo.

echo Installing dependencies to system Python...
pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo Installation failed!
    pause
    goto MENU
) else (
    echo.
    echo Installation completed successfully!
    echo You can now choose option 3 or 4 to run the app.
    pause
    goto MENU
)

:RUN_APP
cls
echo ========================================
echo Running Application (Simple)
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    goto MENU
)

echo Starting Poetry Annotation Tool...
echo Browser will open at: http://localhost:8501
echo.
echo To stop: Close this window or press Ctrl+C
echo ========================================
echo.

streamlit run app.py
goto END

:RUN_WITH_VENV
cls
echo ========================================
echo Running Application (Alternative)
echo ========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    goto MENU
)

echo Starting Poetry Annotation Tool...
echo Browser will open at: http://localhost:8501
echo.
echo To stop: Close this window or press Ctrl+C
echo ========================================
echo.

streamlit run app.py
goto END

:CLEAN_RESTART
cls
echo ========================================
echo Clean Cache and Restart
echo ========================================
echo.

echo Cleaning cache files...
if exist "html_cache" rmdir /s /q "html_cache"
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "src\__pycache__" rmdir /s /q "src\__pycache__"

echo Cache cleaned!
echo.
echo Would you like to:
echo 1. Reinstall dependencies and run
echo 2. Just run the application
echo 3. Return to main menu
echo.
set /p clean_choice="Enter choice (1-3): "

if "%clean_choice%"=="1" goto QUICK_START
if "%clean_choice%"=="2" goto RUN_APP
goto MENU

:EXIT
echo.
echo Thank you for using Poetry Annotation Tool!
echo.
pause
exit

:END
echo.
echo Application has stopped.
echo.
set /p restart="Would you like to return to menu? (y/n): "
if /i "%restart%"=="y" goto MENU
if /i "%restart%"=="yes" goto MENU
exit
