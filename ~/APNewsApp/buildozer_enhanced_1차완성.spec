[app]

# 기본 정보
title = AP News
package.name = apnews
package.domain = com.chathk

# 소스
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json

# 버전
version = 2.1.0

# 의존성 (번역 기능 추가)
requirements = python3,kivy==2.2.1,kivymd==1.1.1,requests,beautifulsoup4,certifi,charset-normalizer,deep-translator

# 권한
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# 안드로이드 설정
android.api = 31
android.minapi = 21
android.archs = arm64-v8a
orientation = portrait
fullscreen = 0


[buildozer]

log_level = 2
warn_on_root = 1
