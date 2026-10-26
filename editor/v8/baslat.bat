@echo off
cd /d "%~dp0"
py -3 csv_ceviri_editor.py
if errorlevel 1 python csv_ceviri_editor.py
pause
