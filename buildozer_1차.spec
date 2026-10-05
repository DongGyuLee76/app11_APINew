[app]
title = AP News
package.name = apnews
package.domain = com.chathk
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.1

# 최소 requirements로 변경
requirements = python3,kivy==2.2.1,kivymd==1.1.1,requests,beautifulsoup4,lxml,html5lib,certifi,android

# 권한
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

android.api = 31
android.minapi = 21
android.archs = arm64-v8a,armeabi-v7a
orientation = portrait

# 중요: 앱 로그 활성화
android.logcat_filters = *:S python:D

[buildozer]
log_level = 2
warn_on_root = 1