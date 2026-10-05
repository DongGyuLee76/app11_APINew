[app]

title = AP News Final
package.name = apnewsfinal
package.domain = com.chathk

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf

version = 2.4.0

# 의존성 (googletrans 포함)
requirements = python3,kivy==2.2.1,kivymd==1.1.1,requests,beautifulsoup4,certifi,charset-normalizer,deep-translator,googletrans==4.0.0rc1

android.permissions = INTERNET,ACCESS_NETWORK_STATE

android.api = 31
android.minapi = 21
android.archs = arm64-v8a
orientation = portrait
fullscreen = 0


[buildozer]

log_level = 2
warn_on_root = 1
