@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
py -3 --version >nul 2>&1
if not errorlevel 1 set "PYTHON=py -3"
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    for %%P in ("%USERPROFILE%\.local\bin\python3.*.exe") do if exist "%%~fP" set "PYTHON="%%~fP""
)
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
    echo Python 3 was not found. Install it from https://www.python.org/downloads/
    echo Tick "Add Python to PATH" during setup, then run this file again.
    pause
    exit /b 1
)

echo Installing dependencies...
%PYTHON% -c "import flask, flask_cors, requests, urllib3, webview" >nul 2>&1
if not errorlevel 1 goto menu
%PYTHON% -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo Installation failed. Check your connection and your Python install.
    pause
    exit /b 1
)

:menu
cls
echo Valinven - Valorant Inventory
echo =============================
echo.
echo   1. Open the interface and sign in
echo   2. Export the inventory to JSON and CSV
echo   3. Sign out ^(forget the saved Riot session^)
echo   4. Quit
echo.
choice /c 1234 /n /m "Choice: "
if errorlevel 4 exit /b 0
if errorlevel 3 goto signout
if errorlevel 2 goto save
if errorlevel 1 goto launch

:launch
echo.
echo Starting...
echo A Riot sign-in window will open when you click "Sign in to Riot".
%PYTHON% valorant_inventory.py
pause
goto menu

:save
echo.
echo Saving the inventory...
echo A Riot sign-in window will open. Neither the game nor Riot Client is needed.
%PYTHON% valorant_inventory.py --save-inventory
pause
goto menu

:signout
echo.
%PYTHON% valorant_inventory.py --logout
pause
goto menu
