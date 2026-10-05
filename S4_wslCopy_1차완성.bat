@echo off
chcp 65001 >nul 2>&1
cls

echo ======================================
echo 프로젝트 파일 복사 (WSL)
echo ======================================
echo.

cd .\~\APNewsApp

REM 현재 Windows 경로
set "WIN_PATH=%CD%"

REM WSL 경로 변환
for /f "usebackq tokens=*" %%i in (`wsl wslpath -u "%WIN_PATH%"`) do set WSL_PATH=%%i

echo [현재 경로]
echo Windows: %WIN_PATH%
echo WSL:     %WSL_PATH%
echo.

REM 사용 가능한 Python 파일 찾기
set "SOURCE_PY="
if exist "%WIN_PATH%\main.py" (
    set "SOURCE_PY=main.py"
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
wsl -d Ubuntu-22.04 bash -c "mkdir -p \~/APNewsApp"
if %errorlevel% equ 0 (
    echo [OK] 완료
) else (
    echo [오류] 폴더 생성 실패
)
echo.

echo [2/4] %SOURCE_PY% -^> main.py 복사 중...
wsl -d Ubuntu-22.04 bash -c "cp '%WSL_PATH%/%SOURCE_PY%' \~/APNewsApp/main.py"
if %errorlevel% equ 0 (
    echo [OK] 복사 완료
) else (
    echo [오류] 파일 복사 실패
)
echo.

echo [3/4] buildozer.spec 복사 중...
if exist "%WIN_PATH%\buildozer.spec" (
    wsl -d Ubuntu-22.04 bash -c "cp '%WSL_PATH%/buildozer.spec' \~/APNewsApp/"
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
    wsl -d Ubuntu-22.04 bash -c "cp '%WSL_PATH%/requirements.txt' \~/APNewsApp/"
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
wsl -d Ubuntu-22.04 bash -c "ls -lh \~/APNewsApp/"
echo.

echo ======================================
echo 파일 복사 완료!
echo ======================================
echo.
echo 복사된 파일 위치: WSL \~/APNewsApp/
echo.
wsl -d Ubuntu-22.04 bash -c "echo '파일 목록:' && ls -1 \~/APNewsApp/"
echo.
echo 다음 단계: S4_build_apk.bat 실행
pause