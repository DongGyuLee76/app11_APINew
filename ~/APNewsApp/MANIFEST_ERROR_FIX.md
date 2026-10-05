# 🔧 AndroidManifest.xml 파싱 오류 해결 가이드

## 📋 에러 로그
```
[DEBUG]:        > Task :processDebugMainManifest FAILED
[DEBUG]:        FAILURE: Build failed with an exception.
[DEBUG]:        * What went wrong:
[DEBUG]:        Execution failed for task ':processDebugMainManifest'.
[DEBUG]:        > com.android.manifmerger.ManifestMerger2$MergeFailureException: Error parsing AndroidManifest.xml
```

---

## 🎯 문제 원인

### **buildozer.spec 파일의 이중 따옴표 문제**

```ini
# ❌ 잘못된 코드 (buildozer_fixed.spec 55번째 줄)
android.apptheme = "@android:style/Theme.NoTitleBar"
```

**문제점:**
- buildozer.spec 파일에서 값을 이중 따옴표(`"..."`)로 감싸면 안 됨
- 빌드 시 명령어 인자로 `'"@android:style/Theme.NoTitleBar"'`가 전달됨
- AndroidManifest.xml 생성 시 XML 속성 값에 이중 따옴표가 포함되어 파싱 오류 발생

**빌드 로그에서 확인:**
```bash
'--android-apptheme', '"@android:style/Theme.NoTitleBar"'  # ❌ 이중 따옴표
```

이것이 AndroidManifest.xml에서:
```xml
android:theme=""@android:style/Theme.NoTitleBar""  <!-- ❌ 파싱 오류 -->
```

---

## ✅ 해결 방법

### **1. buildozer_fixed.spec 수정 (이미 완료)**

```ini
# ✅ 수정된 코드
android.apptheme = @android:style/Theme.NoTitleBar  # 따옴표 제거
```

**올바른 빌드 명령어:**
```bash
'--android-apptheme', '@android:style/Theme.NoTitleBar'  # ✅ 단일 문자열
```

**생성되는 AndroidManifest.xml:**
```xml
android:theme="@android:style/Theme.NoTitleBar"  <!-- ✅ 정상 -->
```

---

## 🚀 다음 단계

### **1. 클린 빌드 실행**

WSL에서 다음 명령어를 실행하세요:

```bash
# APNewsApp 디렉토리로 이동
cd /home/aimecha/APNewsApp

# buildozer.spec 파일 업데이트
# Windows에서 수정한 buildozer_fixed.spec을 복사
cp buildozer_fixed.spec buildozer.spec

# 기존 빌드 폴더 삭제 (중요!)
rm -rf .buildozer

# 클린 빌드
buildozer -v android debug
```

### **2. 빌드가 완료되면**

```bash
# APK 파일 확인
ls -lh bin/

# 디바이스에 설치
adb install -r bin/apnews-1.0.1-arm64-v8a-debug.apk

# 앱 실행
adb shell am start -n com.chathk.apnews/.MainActivity

# 로그 확인
adb logcat | grep -E "python|kivy|APNews"
```

---

## 🔍 추가 확인사항

### **다른 buildozer.spec 설정에서 주의할 점**

1. **따옴표가 필요 없는 경우** (대부분)
   ```ini
   ✅ android.apptheme = @android:style/Theme.NoTitleBar
   ✅ orientation = portrait
   ✅ package.name = apnews
   ```

2. **따옴표가 필요한 경우** (드물음)
   ```ini
   # 공백이 있는 경우에만 필요
   title = "AP News App"  # 공백 있음
   
   # 하지만 가능하면 공백 없이
   title = APNewsApp     # 더 안전함
   ```

3. **절대 이중 따옴표를 사용하지 말 것**
   ```ini
   ❌ android.apptheme = "@android:style/Theme.NoTitleBar"
   ❌ package.name = "com.chathk.apnews"
   ```

---

## 📊 수정 전후 비교

| 항목 | 수정 전 | 수정 후 |
|------|---------|---------|
| **buildozer.spec** | `android.apptheme = "@android:style/Theme.NoTitleBar"` | `android.apptheme = @android:style/Theme.NoTitleBar` |
| **빌드 명령어** | `'--android-apptheme', '"@android:style/Theme.NoTitleBar"'` | `'--android-apptheme', '@android:style/Theme.NoTitleBar'` |
| **AndroidManifest.xml** | `android:theme=""@android:style/..."` (파싱 오류) | `android:theme="@android:style/..."` (정상) |
| **빌드 결과** | ❌ FAILED | ✅ SUCCESS |

---

## 💡 buildozer.spec 파일 작성 규칙

### **기본 원칙**

1. **단순 문자열**: 따옴표 없이 작성
   ```ini
   package.name = apnews
   version = 1.0.1
   orientation = portrait
   ```

2. **경로**: 절대 경로 또는 상대 경로, 따옴표 선택적
   ```ini
   source.dir = .
   icon.filename = %(source.dir)s/icon.png
   ```

3. **리스트**: 쉼표로 구분, 따옴표 없음
   ```ini
   requirements = python3,kivy,kivymd,requests
   android.permissions = INTERNET,ACCESS_NETWORK_STATE
   android.archs = arm64-v8a
   ```

4. **특수 문자**: `@`, `/`, `.` 등은 따옴표 없이 사용 가능
   ```ini
   android.apptheme = @android:style/Theme.NoTitleBar
   package.domain = com.chathk
   ```

5. **공백 포함 시**: 단일 따옴표 사용 (이중 따옴표 금지)
   ```ini
   # 가능하면 공백 없이
   title = APNews

   # 공백 필요 시 단일 따옴표
   title = 'AP News App'
   ```

---

## 🛠️ 문제 지속 시 추가 조치

### **1. AndroidManifest.xml 직접 확인**

```bash
cat /home/aimecha/APNewsApp/.buildozer/android/platform/build-arm64-v8a/dists/apnews/src/main/AndroidManifest.xml
```

### **2. Gradle 로그 상세 확인**

```bash
cd /home/aimecha/APNewsApp
buildozer -v android debug 2>&1 | tee build.log
grep -A 20 "AndroidManifest" build.log
```

### **3. 완전 클린 후 재빌드**

```bash
# 모든 빌드 캐시 삭제
rm -rf .buildozer
rm -rf bin

# Buildozer 캐시 삭제
rm -rf ~/.buildozer/android/platform/build-*

# 재빌드
buildozer android clean
buildozer -v android debug
```

---

## ✅ 해결 확인

수정 후 빌드가 성공하면 다음 메시지를 확인할 수 있습니다:

```
BUILD SUCCESSFUL in XXs
XX actionable tasks: XX executed

Move /home/aimecha/APNewsApp/.buildozer/android/platform/build-arm64-v8a/dists/apnews/build/outputs/apk/debug/apnews-debug.apk to /home/aimecha/APNewsApp/bin/apnews-1.0.1-arm64-v8a-debug.apk
```

이제 APK가 정상적으로 생성됩니다! 🎉

---

## 📝 요약

**문제**: `android.apptheme = "@android:style/Theme.NoTitleBar"` (이중 따옴표)  
**해결**: `android.apptheme = @android:style/Theme.NoTitleBar` (따옴표 제거)  
**결과**: AndroidManifest.xml 파싱 오류 해결 → APK 빌드 성공
