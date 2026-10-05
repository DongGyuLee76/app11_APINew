@echo off
chcp 65001 >nul 2>&1
cls

echo ========================================
echo WSL2 자동 설치 스크립트
echo ========================================
echo.

REM 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] 관리자 권한으로 실행해주세요!
    echo.
    echo 실행 방법:
    echo 1. 일반 CMD를 관리자 권한으로 실행
    echo 2. 이 배치 파일 실행
    echo.
    echo [주의] 아나콘다 프롬프트는 관리자 권한 없음
    echo.
    pause
    exit /b 1
)

echo [1/4] WSL 기능 활성화 중...
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart

echo.
echo [2/4] 가상 머신 플랫폼 활성화 중...
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

echo.
echo [3/4] WSL2를 기본값으로 설정...
wsl --set-default-version 2

echo.
echo [4/4] Ubuntu 설치 중...
wsl --install -d Ubuntu-22.04

echo.
echo ========================================
echo 설치 완료!
echo ========================================
echo.
echo [중요] 다음 단계:
echo 1. 컴퓨터 재부팅
echo 2. 시작 메뉴에서 "Ubuntu 22.04 LTS" 실행
echo 3. 사용자 이름과 비밀번호 설정
echo 4. S2_setup_wsl_environment.bat 실행
echo.
pause