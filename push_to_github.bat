@echo off
title Push PharmaPulse CI to GitHub (asekar01)
color 0A
echo =======================================================
echo   Pushing PharmaPulse CI to GitHub (asekar01)
echo =======================================================
cd /d "%~dp0"

git remote remove origin 2>nul
git remote add origin https://github.com/asekar01/pharmapulse_ci.git
git branch -M main

echo.
echo Connecting to https://github.com/asekar01/pharmapulse_ci.git...
echo.

git push -u origin main

if errorlevel 1 (
    echo.
    echo [ERROR] Git push failed. Please check the message above.
) else (
    echo.
    echo =======================================================
    echo   SUCCESS! PharmaPulse CI is now safely on GitHub:
    echo   https://github.com/asekar01/pharmapulse_ci
    echo =======================================================
)
echo.
pause
