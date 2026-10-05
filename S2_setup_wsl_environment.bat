@echo off
chcp 65001 >nul 2>&1
cls

echo ========================================
echo WSL2 Ubuntu 환경 설정
echo ========================================
echo.

set "WSLENV="
set "WSL_ERR=%TEMP%\wsl_err.log"

echo [환경 확인 중...]
wsl -d Ubuntu-22.04 bash -c "whoami" 2>"%WSL_ERR%" >nul
if %errorlevel% neq 0 (
    echo [오류] Ubuntu가 설치되지 않았거나 초기 설정이 안 됨
    echo.
    echo 해결 방법:
    echo 1. 시작 메뉴에서 "Ubuntu 22.04 LTS" 검색
    echo 2. 실행하여 사용자 설정 완료
    echo 3. 이 스크립트 다시 실행
    echo.
    pause
    exit /b 1
)
echo [OK] Ubuntu 설정 확인
echo.

echo [1/7] 시스템 업데이트 (시간 소요: 5-10분)...
wsl -d Ubuntu-22.04 bash -c "sudo apt update && sudo apt upgrade -y" 2>"%WSL_ERR%"

echo.
echo [2/7] 빌드 도구 설치 (시간 소요: 5-10분)...
wsl -d Ubuntu-22.04 bash -c "sudo apt install -y build-essential git zip unzip" 2>"%WSL_ERR%"

echo.
echo [3/7] Java 설치...
wsl -d Ubuntu-22.04 bash -c "sudo apt install -y openjdk-11-jdk" 2>"%WSL_ERR%"

echo.
echo [4/7] 개발 라이브러리 설치...
wsl -d Ubuntu-22.04 bash -c "sudo apt install -y python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev" 2>"%WSL_ERR%"

echo.
echo [5/7] Python 패키지 업그레이드...
wsl -d Ubuntu-22.04 bash -c "pip3 install --upgrade pip setuptools wheel" 2>"%WSL_ERR%"

echo.
echo [6/7] Buildozer 설치 (시간 소요: 3-5분)...
wsl -d Ubuntu-22.04 bash -c "pip3 install buildozer" 2>"%WSL_ERR%"

echo.
echo [7/7] Cython 설치...
wsl -d Ubuntu-22.04 bash -c "pip3 install cython==0.29.33" 2>"%WSL_ERR%"

echo.
echo [추가] 작업 환경 설정...
wsl -d Ubuntu-22.04 bash -c "mkdir -p \~/APNewsApp" 2>"%WSL_ERR%"
wsl -d Ubuntu-22.04 bash -c "echo 'export PATH=\$PATH:\$HOME/.local/bin' >> \~/.bashrc" 2>"%WSL_ERR%"

echo.
echo [확인] buildozer 설치 확인...
wsl -d Ubuntu-22.04 bash -c "export PATH=\$PATH:\~/.local/bin && buildozer version" 2>"%WSL_ERR%"

if exist "%WSL_ERR%" del "%WSL_ERR%"

echo.
echo ========================================
echo 환경 설정 완료!
echo ========================================
echo.
echo 다음 단계: S3_setup_project.bat 실행
echo.
pause