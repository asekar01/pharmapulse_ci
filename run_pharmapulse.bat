@echo off
title PharmaPulse CI — Clinical Intelligence & Forecasting
color 0B
echo =======================================================
echo   PharmaPulse CI — Competitive Intelligence Terminal
echo   Starting local resilient backend and UI...
echo =======================================================
cd /d "%~dp0"
python main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Could not start PharmaPulse CI with python.
    echo Trying with py launcher...
    py main.py
)
pause
