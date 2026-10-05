[app]

title = AP News Fixed
package.name = apnewsfixed
package.domain = com.chathk

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf

version = 2.3.0

# 의존성 수정 (googletrans 제거, deep-translator 유지)
requirements = python3,kivy==2.2.1,kivymd==1.1.1,requests,beautifulsoup4,certifi,charset-normalizer,deep-translator

android.permissions = INTERNET,ACCESS_NETWORK_STATE

android.api = 31
android.minapi = 21
android.archs = arm64-v8a
orientation = portrait
fullscreen = 0


[buildozer]

log_level = 2
warn_on_root = 1
