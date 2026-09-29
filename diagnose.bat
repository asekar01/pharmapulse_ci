@echo off
title PharmaPulse CI — System Health Check
color 0B
echo =======================================================
echo   PharmaPulse CI — Running Diagnostics & Health Check
echo =======================================================
cd /d "%~dp0"
python backend\diagnostics.py
pause
