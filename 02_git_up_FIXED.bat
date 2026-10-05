@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo   From Local To Cloud : git push (LFS)
echo   Large File Support Version
echo ========================================

REM ============================================
REM [0] Git network buffer configuration
REM ============================================
git config http.postBuffer 524288000
git config http.lowSpeedLimit 0
git config http.lowSpeedTime 999
git config core.compression 0
echo [OK] Network buffer: 500MB / Timeout: unlimited

REM ============================================
REM [1] Check remote origin
REM ============================================
git remote get-url origin >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Remote origin is not set.
    echo Please run: git remote add origin YOUR_GITHUB_URL
    pause
    exit /b 1
)

REM ============================================
REM [2] Git LFS setup
REM ============================================
echo.
echo [Git LFS Status Check]
git lfs version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Git LFS is not installed.
    echo Download: https://git-lfs.github.com/
    echo.
    set /p lfs_skip=Continue without LFS? Y/N: 
    if /i "!lfs_skip!" neq "Y" (
        echo Aborted.
        pause
        exit /b 1
    )
) else (
    echo [OK] Git LFS detected
    git lfs install >nul 2>&1
    echo [OK] Git LFS initialized

    echo.
    echo [LFS Tracking Pattern Registration]
    git lfs track "*.dat"  >nul 2>&1
    git lfs track "*.inp"  >nul 2>&1
    git lfs track "*.xlsx"  >nul 2>&1
    git lfs track "*.xlsm"  >nul 2>&1
    git lfs track "*.xls"  >nul 2>&1
    git lfs track "*.pdf"  >nul 2>&1
    git lfs track "*.pptx"  >nul 2>&1
    git lfs track "*.docx"  >nul 2>&1
    git lfs track "*.mp4"  >nul 2>&1
    git lfs track "*.avi"  >nul 2>&1
    git lfs track "*.png"  >nul 2>&1
    git lfs track "*.jpg"  >nul 2>&1
    git lfs track "*.zip"  >nul 2>&1
    git lfs track "*.7z"  >nul 2>&1
    git lfs track "*.rar"  >nul 2>&1
    git lfs track "*.odb"  >nul 2>&1
    git lfs track "*.sim"  >nul 2>&1
    git lfs track "*.fil"  >nul 2>&1
    git lfs track "*.stt"  >nul 2>&1
    git lfs track "*.mdl"  >nul 2>&1
    git lfs track "*.res"  >nul 2>&1
    git lfs track "*.prt"  >nul 2>&1
    git lfs track "*.joblib"  >nul 2>&1
    git lfs track "*.Parquet"  >nul 2>&1
    git lfs track "*.parquet"  >nul 2>&1
    git lfs track "*.mat"  >nul 2>&1
    git lfs track "*.out"  >nul 2>&1

    echo [OK] LFS tracking patterns registered
    echo.
    echo [Current LFS Tracking List]
    git lfs track
)

REM ============================================
REM [3] Check current branch
REM ============================================
for /f "usebackq tokens=*" %%b in (`git branch --show-current`) do set currentBranch=%%b
echo.
echo Current Branch : !currentBranch!

REM ============================================
REM [4] Delete Excel temp files
REM ============================================
echo.
echo [Cleaning Excel Temp Files]
for /f "usebackq delims=" %%i in (`dir /s /b /a-d 2^>nul ^| findstr /i "\\~$"`) do (
    echo Deleting: %%i
    del /f /q "%%i" 2>nul
)
echo [OK] Temp files cleaned

REM ============================================
REM [5] Check .gitignore
REM ============================================
echo.
echo [Checking .gitignore]
if exist .gitignore (
    echo [OK] .gitignore exists
) else (
    echo [WARNING] .gitignore not found
)

REM ============================================
REM [6] Scan large files
REM ============================================
echo.
echo [Scanning Large Files 100MB+]
set largeFileFound=0
set largeFileCount=0

for /r %%f in (*) do (
    set "filesize=%%\~zf"
    set "filename=%%\~nxf"
    
    if !filesize! GTR 104857600 (
        set /a largeFileCount+=1
        set /a sizemb=!filesize!/1048576
        
        echo [WARNING] Large: !filename! - !sizemb! MB
        set largeFileFound=1
    )
)

echo.
if !largeFileCount! GTR 0 (
    echo Total large files: !largeFileCount!
) else (
    echo [OK] No files over 100MB
)

if !largeFileFound! equ 1 (
    echo.
    echo [WARNING] Large files detected
    echo   - GitHub limit: 100MB per file
    echo   - Git LFS tracking required
    echo.
    set /p cont=Continue? Y/N: 
    if /i "!cont!" neq "Y" (
        echo Aborted.
        pause
        exit /b 1
    )
)

REM ============================================
REM [7] Git Status
REM ============================================
echo.
echo [Git Status]
git --no-pager status --porcelain

git --no-pager status --porcelain 2>nul | findstr /r "." >nul
if %errorlevel% neq 0 (
    echo [INFO] No changes.
    pause
    exit /b 0
)

REM ============================================
REM [8] git add
REM ============================================
echo.
echo [git add .]
git add .
if %errorlevel% neq 0 (
    echo [ERROR] git add failed.
    pause
    exit /b 1
)
echo [OK] git add completed

REM ============================================
REM [9] Staged files
REM ============================================
echo.
echo [Staged Files]
git --no-pager diff --cached --name-only

REM ============================================
REM [10] Commit
REM ============================================
echo.
set /p commit_message=Enter commit message: 
if "!commit_message!"=="" (
    echo [ERROR] Empty commit message.
    pause
    exit /b 1
)

echo.
echo [git commit]
git commit -m "!commit_message!"
if %errorlevel% neq 0 (
    echo [ERROR] git commit failed.
    pause
    exit /b 1
)
echo [OK] Commit completed

REM ============================================
REM [11] Rebase setup
REM ============================================
git config pull.rebase true
git config rebase.autoStash true

REM ============================================
REM [12] git pull
REM ============================================
echo.
echo [git pull --rebase]
git pull --rebase origin !currentBranch!
if %errorlevel% neq 0 (
    echo [ERROR] git pull failed.
    pause
    exit /b 1
)
echo [OK] Pull completed

REM ============================================
REM [13] git push
REM ============================================
echo.
echo [git push]

git lfs version >nul 2>&1
if %errorlevel% equ 0 (
    echo [LFS] Pushing LFS objects...
    git lfs push origin !currentBranch! --all
)

git push origin !currentBranch!
if %errorlevel% neq 0 (
    echo [ERROR] git push failed.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  [OK] SUCCESS!
echo  Branch: !currentBranch!
echo ============================================
pause
endlocal
exit /b 0
