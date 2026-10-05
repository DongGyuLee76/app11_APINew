@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
cls

echo ======================================
echo 프로젝트 파일 복사 (WSL)
echo ======================================
echo.

REM 현재 Windows 경로
set "WIN_PATH=%CD%"

REM WSL 경로 변환 (간단한 방법)
for /f "usebackq tokens=*" %%i in (`wsl wslpath -u "%WIN_PATH%"`) do set WSL_PATH=%%i

echo [현재 경로]
echo Windows: %WIN_PATH%
echo WSL:     %WSL_PATH%
echo.

REM 경로 변환 실패 체크
if "%WSL_PATH%"=="" (
    echo [오류] WSL 경로 변환 실패
    echo WSL이 설치되어 있는지 확인하세요.
    pause
    exit /b 1
)

REM 사용 가능한 Python 파일 찾기
set "SOURCE_PY="
if exist "%WIN_PATH%\AP_news_v1_app.py" (
    set "SOURCE_PY=AP_news_v1_app.py"
) 


if "%SOURCE_PY%"=="" (
    echo [오류] 복사할 Python 파일을 찾을 수 없습니다.
    echo.
    dir /b "%WIN_PATH%\*.py"
    pause
    exit /b 1
)

echo [복사할 파일: %SOURCE_PY%]
echo.

echo [1/5] APNewsApp 폴더 생성...
wsl -d Ubuntu-22.04 bash -c "mkdir -p \~/APNewsApp"
if %errorlevel% equ 0 (
    echo [OK] 완료
) else (
    echo [오류] 폴더 생성 실패
)
echo.

echo [2/5] %SOURCE_PY% -^> main.py 복사 중...
wsl -d Ubuntu-22.04 bash -c "cp '%WSL_PATH%/%SOURCE_PY%' \~/APNewsApp/"
wsl -d Ubuntu-22.04 bash -c "cp '%WSL_PATH%/%SOURCE_PY%' \~/APNewsApp/main.py"
if %errorlevel% equ 0 (
    echo [OK] 복사 완료
) else (
    echo [오류] 파일 복사 실패
    wsl -d Ubuntu-22.04 bash -c "echo '파일 경로: %WSL_PATH%/%SOURCE_PY%'"
)
echo.

echo [3/5] buildozer.spec 복사 중...
wsl -d Ubuntu-22.04 bash -c "cp '%WSL_PATH%/buildozer.spec' \~/APNewsApp/"
if %errorlevel% equ 0 (
    echo [OK] 복사 완료
) else (
    echo [오류] 파일 복사 실패
)
echo.

echo [4/5] requirements.txt 복사 중...
wsl -d Ubuntu-22.04 bash -c "cp '%WSL_PATH%/requirements.txt' \~/APNewsApp/"
if %errorlevel% equ 0 (
    echo [OK] 복사 완료
) else (
    echo [오류] 파일 복사 실패
)
echo.

echo [5/5] 복사된 파일 확인...
echo.
wsl -d Ubuntu-22.04 bash -c "ls -lh \~/APNewsApp/"
echo.

echo ======================================
echo 파일 복사 완료!
echo ======================================
echo.
echo 복사된 파일 위치: WSL \~/APNewsApp/
echo.
wsl -d Ubuntu-22.04 bash -c "echo '복사된 파일 목록:' && ls -1 \~/APNewsApp/"
echo.
echo 다음 단계: S4_build_apk_conda.bat 실행
pause