@echo off
chcp 65001 >nul 2>&1
cls

echo ========================================
echo APK 핸드폰 설치 도구
echo ========================================
echo.

REM ADB 설치 확인
where adb >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] ADB가 설치되어 있지 않습니다.
    echo.
    echo ========================================
    echo ADB 설치 방법
    echo ========================================
    echo.
    echo [방법 1] winget 사용 (Windows 11/10)
    echo winget install Google.PlatformTools
    echo.
    echo [방법 2] 수동 설치
    echo 1. https://developer.android.com/studio/releases/platform-tools
    echo 2. "Download SDK Platform-Tools for Windows" 클릭
    echo 3. 압축 해제 후 C:\platform-tools로 이동
    echo 4. 시스템 환경 변수 PATH에 추가:
    echo    - 내 PC 우클릭 -^> 속성
    echo    - 고급 시스템 설정
    echo    - 환경 변수
    echo    - 시스템 변수의 Path 선택 -^> 편집
    echo    - 새로 만들기 -^> C:\platform-tools 입력
    echo    - 확인
    echo 5. 터미널 재시작
    echo.
    pause
    exit /b 1
)

echo [OK] ADB가 설치되어 있습니다.
echo.

REM APK 파일 찾기
set "APK_FILE="
set "APK_COUNT=0"

for %%F in (*.apk) do (
    set "APK_FILE=%%F"
    set /a APK_COUNT+=1
)

if "%APK_FILE%"=="" (
    echo [오류] 현재 폴더에 APK 파일이 없습니다.
    echo.
    echo 현재 폴더: %CD%
    echo.
    echo 해결 방법:
    echo 1. S4_build_apk.bat를 먼저 실행
    echo 2. 또는 APK 파일을 이 폴더로 복사
    echo.
    pause
    exit /b 1
)

echo ========================================
echo APK 파일 발견
echo ========================================
echo.
echo 파일명: %APK_FILE%

for %%F in ("%APK_FILE%") do (
    echo 크기:   %%\~zF bytes
    echo 수정일: %%\~tF
)

echo.
echo ========================================
echo 핸드폰 연결 확인
echo ========================================
echo.

echo [1/4] 연결된 디바이스 확인...
adb devices
echo.

echo [2/4] USB 디버깅 활성화 확인
echo.
echo 핸드폰에서 다음 설정을 확인하세요:
echo.
echo ┌─────────────────────────────────────┐
echo │ 1. 개발자 옵션 활성화               │
echo │    - 설정 -^> 휴대전화 정보         │
echo │    - 빌드번호 7번 연속 탭           │
echo │                                      │
echo │ 2. USB 디버깅 활성화                │
echo │    - 설정 -^> 개발자 옵션           │
echo │    - USB 디버깅 켜기                │
echo │                                      │
echo │ 3. USB 연결                          │
echo │    - USB 케이블로 컴퓨터와 연결     │
echo │    - "USB 디버깅 허용" 팝업에서 확인│
echo └─────────────────────────────────────┘
echo.
pause

echo.
echo [3/4] APK 설치 중...
echo.

adb install -r "%APK_FILE%"

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo 설치 완료!
    echo ========================================
    echo.
    echo 핸드폰에서 "AP News" 앱을 찾아 실행하세요.
    echo.
    echo 앱 이름: AP News
    echo 패키지: com.chathk.apnews
    echo.
) else (
    echo.
    echo ========================================
    echo 설치 실패
    echo ========================================
    echo.
    echo 가능한 원인:
    echo 1. USB 디버깅이 비활성화됨
    echo 2. 디바이스가 연결되지 않음
    echo 3. 알 수 없는 소스 허용 필요
    echo 4. 기존 앱과 서명 불일치
    echo.
    echo 해결 방법:
    echo 1. "adb devices" 명령어로 디바이스 확인
    echo 2. 핸드폰에서 기존 앱 제거 후 재시도
    echo 3. USB 케이블 다시 연결
    echo.
)

echo [4/4] 연결 상태 확인
adb devices

echo.
pause