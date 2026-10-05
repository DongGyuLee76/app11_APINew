@echo off
echo WSL 설정 변경 (Windows PATH 상속 비활성화)
wsl -d Ubuntu-22.04 bash -c "sudo bash -c 'echo [interop] > /etc/wsl.conf && echo appendWindowsPath = false >> /etc/wsl.conf'"
echo 설정 완료. WSL을 재시작하세요.
wsl --shutdown
pause