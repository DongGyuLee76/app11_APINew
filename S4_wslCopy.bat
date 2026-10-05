@echo off
chcp 65001 >nul 2>&1
cls

echo ======================================
echo 프로젝트 파일 복사 (WSL)
echo ======================================
echo.

REM 현재 Windows 경로
set "WIN_PATH=%CD%"

REM WSL 경로 변환
for /f "usebackq tokens=*" %%i in (`wsl wslpath -u "%WIN_PATH%"`) do set "WSL_PATH=%%i"

echo [현재 경로]
echo Windows: %WIN_PATH%
echo WSL:     %WSL_PATH%
echo.

REM WSL 사용자명 가져오기
for /f "usebackq tokens=*" %%i in (`wsl -d Ubuntu-22.04 bash -c "whoami"`) do set "WSL_USER=%%i"

if "%WSL_USER%"=="" (
    echo [오류] WSL 사용자명을 가져오지 못했습니다.
    pause
    exit /b 1
)

set "WSL_APP_DIR=/home/%WSL_USER%/APNewsApp"

REM 사용 가능한 Python 파일 찾기
set "SOURCE_PY="
if exist "%WIN_PATH%\main.py" (
    set "SOURCE_PY=main.py"
) else if exist "%WIN_PATH%\AP_news_v1_app.py" (
    set "SOURCE_PY=AP_news_v1_app.py"
) else if exist "%WIN_PATH%\app.py" (
    set "SOURCE_PY=app.py"
)

if "%SOURCE_PY%"=="" (
    echo [오류] 복사할 Python 파일을 찾을 수 없습니다.
    echo.
    echo [현재 디렉토리의 Python 파일 목록:]
    dir /b "%WIN_PATH%\*.py" 2>nul
    echo.
    pause
    exit /b 1
)

echo [복사할 파일: %SOURCE_PY%]
echo.

echo [1/4] APNewsApp 폴더 생성...
wsl -d Ubuntu-22.04 bash -c "mkdir -p '%WSL_APP_DIR%'"
if %errorlevel% equ 0 (
    echo [OK] 완료
) else (
    echo [오류] 폴더 생성 실패
    echo 경로: %WSL_APP_DIR%
    pause
    exit /b 1
)
echo.

echo [2/4] %SOURCE_PY% -^> main.py 복사 중...
wsl -d Ubuntu-22.04 bash -c "cp '%WSL_PATH%/%SOURCE_PY%' '%WSL_APP_DIR%/main.py'"
if %errorlevel% equ 0 (
    echo [OK] 복사 완료
) else (
    echo [오류] 파일 복사 실패
    echo 경로: %WSL_PATH%/%SOURCE_PY%
    pause
    exit /b 1
)
echo.

echo [3/4] buildozer.spec 복사 중...
if exist "%WIN_PATH%\buildozer.spec" (
    wsl -d Ubuntu-22.04 bash -c "cp '%WSL_PATH%/buildozer.spec' '%WSL_APP_DIR%/'"
    if %errorlevel% equ 0 (
        echo [OK] 복사 완료
    ) else (
        echo [오류] 파일 복사 실패
    )
) else (
    echo [경고] buildozer.spec 파일이 없습니다. buildozer가 자동 생성합니다.
)
echo.

echo [4/4] requirements.txt 복사 중...
if exist "%WIN_PATH%\requirements.txt" (
    wsl -d Ubuntu-22.04 bash -c "cp '%WSL_PATH%/requirements.txt' '%WSL_APP_DIR%/'"
    if %errorlevel% equ 0 (
        echo [OK] 복사 완료
    ) else (
        echo [오류] 파일 복사 실패
    )
) else (
    echo [경고] requirements.txt 파일이 없습니다.
)
echo.

echo [복사된 파일 확인]
echo.
wsl -d Ubuntu-22.04 bash -c "ls -lh '%WSL_APP_DIR%/'"
echo.

echo ======================================
echo 파일 복사 완료!
echo ======================================
echo.
echo 복사된 파일 위치:
echo   WSL: %WSL_APP_DIR%/
echo   Windows: \\wsl$\Ubuntu-22.04\home\%WSL_USER%\APNewsApp\
echo.

echo 파일 목록:
wsl -d Ubuntu-22.04 bash -c "ls -1 '%WSL_APP_DIR%/'"
echo.

REM echo Windows 탐색기로 여시겠습니까? (Y/N)
REM set /p open_explorer=
REM if /i "%open_explorer%"=="Y" (
REM     start explorer.exe "\\wsl$\Ubuntu-22.04\home\%WSL_USER%\APNewsApp"
REM )

echo.
echo 다음 단계: S5_build_apk.bat 실행
pause