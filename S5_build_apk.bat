@echo off
chcp 65001 >nul 2>&1
cls

echo ========================================
echo APK 빌드 시작
echo ========================================
echo.

set "WSLENV="
set "WSL_ERR=%TEMP%\wsl_err.log"

echo [환경 확인 중...]
echo.

REM buildozer 설치 확인
wsl -d Ubuntu-22.04 bash -c "export PATH=$PATH:~/.local/bin && which buildozer" >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] buildozer가 설치되지 않았습니다!
    echo.
    echo 해결 방법:
    echo 1. S2_setup_wsl_environment.bat를 먼저 실행하세요.
    echo.
    echo 또는 수동 확인:
    echo wsl -d Ubuntu-22.04 bash -c "which buildozer"
    echo wsl -d Ubuntu-22.04 bash -c "ls -la ~/.local/bin/buildozer"
    echo.
    pause
    exit /b 1
)
echo [OK] buildozer 설치 확인

REM 프로젝트 파일 확인
wsl -d Ubuntu-22.04 bash -c "test -f ~/APNewsApp/main.py" 2>nul
if %errorlevel% neq 0 (
    echo [오류] ~/APNewsApp/main.py가 없습니다!
    echo.
    echo 해결 방법:
    echo S3_setup_project.bat를 먼저 실행하세요.
    echo.
    pause
    exit /b 1
)
echo [OK] 프로젝트 파일 확인

wsl -d Ubuntu-22.04 bash -c "test -f ~/APNewsApp/buildozer.spec" 2>nul
if %errorlevel% neq 0 (
    echo [경고] buildozer.spec 파일이 없습니다. 기본 설정으로 생성됩니다.
) else (
    echo [OK] buildozer.spec 확인
)
echo.

echo ========================================
echo 빌드 옵션 선택
echo ========================================
echo.
echo [1] Debug APK
echo     - 용도: 테스트, 개발
echo     - 시간: 10-20분 (첫 빌드 30-60분)
echo     - 크기: 약 50MB
echo.
echo [2] Release APK
echo     - 용도: 배포, 출시
echo     - 시간: 20-40분
echo     - 크기: 약 40MB (최적화)
echo.
echo [3] Clean 빌드
echo     - 용도: 오류 발생 시
echo     - 시간: 30-60분
echo     - 참고: 캐시 삭제 후 빌드
echo.
echo [0] 취소
echo.
echo ========================================
set /p choice=선택 (0-3): 

if "%choice%"=="0" exit /b 0

echo.

if "%choice%"=="1" (
    echo ========================================
    echo Debug APK 빌드 시작
    echo ========================================
    echo.
    echo [참고] 첫 빌드는 SDK/NDK 다운로드로 시간이 오래 걸립니다.
    echo        인터넷 연결을 유지하고 기다려주세요.
    echo.
    pause
    echo.
    echo 빌드 중... (진행 상황이 터미널에 표시됩니다)
    echo.
    
    wsl -d Ubuntu-22.04 bash -c "export PATH=$PATH:~/.local/bin && cd ~/APNewsApp && buildozer android debug"
    set "BUILD_RESULT=%errorlevel%"
    
) else if "%choice%"=="2" (
    echo ========================================
    echo Release APK 빌드 시작
    echo ========================================
    echo.
    pause
    echo.
    
    wsl -d Ubuntu-22.04 bash -c "export PATH=$PATH:~/.local/bin && cd ~/APNewsApp && buildozer android release"
    set "BUILD_RESULT=%errorlevel%"
    
) else if "%choice%"=="3" (
    echo ========================================
    echo Clean 후 Debug 빌드 시작
    echo ========================================
    echo.
    echo [경고] 캐시가 삭제되어 빌드 시간이 길어집니다.
    echo.
    pause
    echo.
    
    wsl -d Ubuntu-22.04 bash -c "export PATH=$PATH:~/.local/bin && cd ~/APNewsApp && buildozer android clean && buildozer android debug"
    set "BUILD_RESULT=%errorlevel%"
    
) else (
    echo [오류] 잘못된 선택입니다.
    pause
    exit /b 1
)

echo.
echo ========================================
echo 빌드 결과 확인
echo ========================================
echo.

REM APK 파일 확인
wsl -d Ubuntu-22.04 bash -c "ls ~/APNewsApp/bin/*.apk 2>/dev/null" >nul 2>&1
if %errorlevel% equ 0 (
    echo [성공] APK 파일이 생성되었습니다!
    echo.
    
    echo APK 정보:
    wsl -d Ubuntu-22.04 bash -c "ls -lh ~/APNewsApp/bin/*.apk"
    echo.
    
    REM Windows 경로로 변환
    set "WIN_PATH=%CD%"
    for /f "usebackq tokens=*" %%i in (`wsl wslpath -u "%WIN_PATH%"`) do set "WSL_PATH=%%i"
    
    echo Windows로 복사 중...
    wsl -d Ubuntu-22.04 bash -c "cp ~/APNewsApp/bin/*.apk '%WSL_PATH%/'" 2>nul
    
    if exist "*.apk" (
        echo [OK] 복사 완료
        echo.
        echo ========================================
        echo 빌드 완료!
        echo ========================================
        echo.
        echo APK 파일 위치: %CD%
        echo.
        echo 파일 목록:
        dir /b *.apk
        echo.
        for %%F in (*.apk) do (
            echo 파일명: %%F
            echo 크기: %%~zF bytes
        )
        echo.
        start explorer "%CD%"
    ) else (
        echo [경고] Windows로 복사 실패
        echo.
        echo WSL에서 직접 확인하세요:
        echo wsl -d Ubuntu-22.04 bash -c "ls -lh ~/APNewsApp/bin/"
        echo.
        echo 수동 복사 방법:
        echo wsl -d Ubuntu-22.04 bash -c "cp ~/APNewsApp/bin/*.apk /mnt/c/Users/%USERNAME%/Desktop/"
    )
    
) else (
    echo [실패] APK 파일이 생성되지 않았습니다.
    echo.
    echo 빌드 로그 확인 (마지막 50줄):
    echo.
    wsl -d Ubuntu-22.04 bash -c "tail -n 50 ~/.buildozer/logs/buildozer.log 2>/dev/null || echo '로그 파일을 찾을 수 없습니다.'"
    echo.
    echo ----------------------------------------
    echo 전체 로그 보기:
    echo wsl -d Ubuntu-22.04 bash -c "cat ~/.buildozer/logs/buildozer.log"
    echo.
    echo 일반적인 오류 해결 방법:
    echo 1. Clean 빌드 시도 (옵션 3)
    echo 2. WSL 재시작: wsl --shutdown
    echo 3. 디스크 공간 확인: wsl -d Ubuntu-22.04 bash -c "df -h"
)

if exist "%WSL_ERR%" del "%WSL_ERR%" 2>nul

echo.
pause