@echo off
title Push PharmaPulse CI to GitHub (asekar01)
color 0A
echo =======================================================
echo   Pushing PharmaPulse CI to GitHub (asekar01)
echo =======================================================
cd /d "%~dp0"

git remote remove origin 2>nul
git remote add origin https://github.com/asekar01/pharmapulse-ci.git
git branch -M main

echo.
echo Connecting to https://github.com/asekar01/pharmapulse-ci.git...
echo (If prompted, sign in with your GitHub browser window or Personal Access Token)
echo.

git push -u origin main

if errorlevel 1 (
    echo.
    echo [NOTE] If this is your first push, please make sure you created 
    echo the empty repository 'pharmapulse-ci' at:
    echo https://github.com/new
) else (
    echo.
    echo =======================================================
    echo   SUCCESS! PharmaPulse CI is now safely on GitHub:
    echo   https://github.com/asekar01/pharmapulse-ci
    echo =======================================================
)
echo.
pause
