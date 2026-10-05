@echo off
setlocal enabledelayedexpansion

:: Force English output for git and system commands
chcp 65001 > nul
set LANG=en_US
set LC_ALL=en_US

echo ========================================
echo   From Cloud To Local : git pull
echo ========================================

:: Remote origin check
git remote get-url origin >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Remote origin is not set.
    echo Please run: git remote add origin https://github.com/DongGyuLee76/HK_DX_Model.git
    pause
    exit /b 1
)

:: Check local changes BEFORE showing branch list
echo.
echo ### Checking local changes ###
git --no-pager status --porcelain 2>nul | findstr /r "." >nul
if %errorlevel% equ 0 (
    echo [WARN] Uncommitted local changes detected:
    git --no-pager status --porcelain
    echo.
    echo Select how to handle local changes:
    echo   [1] Stash and continue (recommended)
    echo   [2] Discard all local changes (WARNING: cannot undo)
    echo   [3] Cancel
    echo.
    set /p choice=Select (1/2/3): 
    if "!choice!"=="1" (
        echo.
        echo ### git stash ###
        git stash
        if %errorlevel% neq 0 (
            echo [ERROR] git stash failed.
            pause
            exit /b 1
        )
        echo [OK] Stash saved.
        set STASHED=1
    ) else if "!choice!"=="2" (
        echo [WARN] Discard mode selected.
        set STASHED=0
    ) else (
        echo Cancelled.
        pause
        exit /b 0
    )
) else (
    echo [OK] No local changes.
    set STASHED=0
)

:: Show branch list
echo.
echo ### Branch List ###
git branch

:: Input branch name
echo.
set /p branchName=Enter branch name (default: main): 
if "!branchName!"=="" set branchName=main

:: Switch branch
echo.
echo ### git checkout !branchName! ###
git checkout !branchName!
if %errorlevel% neq 0 (
    echo [ERROR] Branch checkout failed: !branchName!
    echo Available branches:
    git branch
    pause
    exit /b 1
)

:: Fetch from remote
echo.
echo ### git fetch origin ###
git fetch origin
if %errorlevel% neq 0 (
    echo [ERROR] git fetch failed. Check network connection.
    pause
    exit /b 1
)

:: Reset to remote branch
echo.
echo ### git reset --hard origin/!branchName! ###
git reset --hard origin/!branchName!
if %errorlevel% neq 0 (
    echo [ERROR] git reset failed.
    git status
    pause
    exit /b 1
)

:: Restore stash if saved
if "!STASHED!"=="1" (
    echo.
    echo ### git stash pop ###
    git stash pop
    if %errorlevel% neq 0 (
        echo [WARN] Stash pop conflict detected.
        echo Please resolve conflicts manually, then run: git stash drop
        git status
    ) else (
        echo [OK] Stash restored.
    )
)

:: Show recent log
echo.
echo ### Recent commits (last 5) ###
git --no-pager log --oneline -5

echo.
echo [OK] All done! Cloud -> Local sync complete. Branch: !branchName!
pause
endlocal
exit /b 0