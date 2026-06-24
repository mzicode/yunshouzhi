@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1

echo Installing Python dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto failed
python -m pip install -r requirements.txt
if errorlevel 1 goto failed

echo Cleaning old Windows build output...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building CloudPhoneManager.exe...
python -m PyInstaller --clean --noconfirm CloudPhoneManager.spec
if errorlevel 1 goto failed

echo.
echo Build finished. The exe is here:
echo %cd%\dist\CloudPhoneManager.exe
pause
exit /b 0

:failed
echo.
echo Build failed. Please copy the error above and send it back for checking.
pause
exit /b 1
