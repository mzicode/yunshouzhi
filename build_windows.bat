@echo off
setlocal

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --onefile --windowed --name CloudPhoneManager --add-data "assets;assets" main.py

echo.
echo Build finished. The exe is here:
echo dist\CloudPhoneManager.exe
pause
