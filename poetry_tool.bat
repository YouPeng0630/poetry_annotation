@echo off
setlocal EnableDelayedExpansion

:MENU
cls
echo ========================================
echo    Poetry Annotation Tool
echo ========================================
echo.
echo Please choose an option:
echo.
echo 1. Install and Run
echo 2. Run Application
echo.
echo ========================================
set /p choice="Enter your choice (1-2): "

if "%choice%"=="1" goto INSTALL_AND_RUN
if "%choice%"=="2" goto RUN_APP
echo Invalid choice. Please try again.
pause
goto MENU

:INSTALL_AND_RUN
cls
echo ========================================
echo Install and Run
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

streamlit run src/app.py
goto END

:RUN_APP
cls
echo ========================================
echo Run Application
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

streamlit run src/app.py
goto END

:END
echo.
echo Application has stopped.
echo.
set /p restart="Would you like to return to menu? (y/n): "
if /i "%restart%"=="y" goto MENU
if /i "%restart%"=="yes" goto MENU
exit