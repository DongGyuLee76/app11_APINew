#!/bin/bash

# AP News 앱 수정사항 적용 스크립트

echo "============================================"
echo "AP News App - 안드로이드 빌드 오류 수정 적용"
echo "============================================"
echo ""

# 현재 디렉토리 확인
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "작업 디렉토리: $SCRIPT_DIR"
echo ""

# 백업 디렉토리 생성
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "1. 기존 파일 백업 중..."
if [ -f "main.py" ]; then
    cp main.py "$BACKUP_DIR/main.py"
    echo "   ✓ main.py 백업 완료"
fi

if [ -f "buildozer.spec" ]; then
    cp buildozer.spec "$BACKUP_DIR/buildozer.spec"
    echo "   ✓ buildozer.spec 백업 완료"
fi

if [ -f "requirements.txt" ]; then
    cp requirements.txt "$BACKUP_DIR/requirements.txt"
    echo "   ✓ requirements.txt 백업 완료"
fi

echo ""
echo "2. 수정된 파일 적용 중..."

# main.py 교체
if [ -f "main_fixed.py" ]; then
    cp main_fixed.py main.py
    echo "   ✓ main.py 수정 적용 완료"
else
    echo "   ✗ main_fixed.py 파일을 찾을 수 없습니다!"
fi

# buildozer.spec 교체
if [ -f "buildozer_fixed.spec" ]; then
    cp buildozer_fixed.spec buildozer.spec
    echo "   ✓ buildozer.spec 수정 적용 완료"
else
    echo "   ✗ buildozer_fixed.spec 파일을 찾을 수 없습니다!"
fi

# requirements.txt 교체
if [ -f "requirements_fixed.txt" ]; then
    cp requirements_fixed.txt requirements.txt
    echo "   ✓ requirements.txt 수정 적용 완료"
else
    echo "   ✗ requirements_fixed.txt 파일을 찾을 수 없습니다!"
fi

echo ""
echo "3. 기존 빌드 캐시 정리 중..."

# 기존 빌드 삭제
if [ -d ".buildozer" ]; then
    rm -rf .buildozer
    echo "   ✓ .buildozer 폴더 삭제 완료"
fi

if [ -d "bin" ]; then
    rm -rf bin
    echo "   ✓ bin 폴더 삭제 완료"
fi

echo ""
echo "============================================"
echo "적용 완료!"
echo "============================================"
echo ""
echo "백업 파일 위치: $BACKUP_DIR"
echo ""
echo "다음 단계:"
echo "1. buildozer -v android debug"
echo "2. adb install -r bin/apnews-*.apk"
echo "3. adb logcat | grep python  (오류 확인)"
echo ""
echo "문제가 발생하면 다음 명령으로 복원 가능:"
echo "   cp $BACKUP_DIR/* ."
echo ""
