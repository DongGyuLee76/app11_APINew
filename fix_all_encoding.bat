@echo off
setlocal enabledelayedexpansion

echo ======================================
echo 배치 파일 인코딩 자동 변환기
echo ======================================
echo.

echo 현재 폴더: %CD%
echo.
echo 모든 .bat 파일을 ANSI(CP949)로 변환합니다.
echo.
pause

set count=0

for %%F in (*.bat) do (
    if not "%%F"=="fix_all_encoding.bat" (
        echo 변환 중: %%F
        
        rem PowerShell로 UTF-8을 ANSI로 변환
        powershell -Command "$content = Get-Content '%%F' -Encoding UTF8 -Raw; $Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $False; [System.IO.File]::WriteAllLines('%%F.temp', $content, [System.Text.Encoding]::Default)"
        
        if exist "%%F.temp" (
            del "%%F"
            ren "%%F.temp" "%%F"
            set /a count+=1
        )
    )
)

echo.
echo ======================================
echo 변환 완료: %count%개 파일
echo ======================================
echo.
echo 이제 배치 파일을 실행하면 한글이 정상 표시됩니다.
pause