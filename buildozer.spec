[app]

# (str) Title of your application
title = AP News

# (str) Package name
package.name = apnews

# (str) Package domain (needed for android/ios packaging)
package.domain = com.chathk

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (comma separated)
source.include_exts = py,png,jpg,kv,atlas,json

# (str) Application versioning (method 1)
version = 1.0.1

# (list) Application requirements
# eng-to-ipa 제거 (안드로이드 호환성 문제)
requirements = python3,kivy==2.2.1,kivymd==1.1.1,requests,beautifulsoup4,gtts,googletrans==4.0.0rc1,nltk,certifi,charset-normalizer

# (list) Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# (str) Icon of the application
#icon.filename = %(source.dir)s/icon.png

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/presplash.png

# (int) Target Android API
android.api = 31

# (int) Minimum API your APK will support
android.minapi = 21

# (list) Supported architectures
android.archs = arm64-v8a

# (str) Application orientation
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (str) Android entry point
#android.entrypoint = org.kivy.android.PythonActivity

# (bool) Use --private data storage
android.private_storage = True

# (str) Android app theme
android.apptheme = "@android:style/Theme.NoTitleBar"

# (list) Android application meta-data
#android.meta_data =

# (str) Android logcat filters
#android.logcat_filters = *:S python:D

# (int) Android: max Java heap size
#android.heap_size = 512m

# (bool) Copy library instead of making a libpymodules.so
#android.copy_libs = 1

# (str) The Android arch to build for
#android.arch = armeabi-v7a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) XML file for custom backup rules
#android.backup_rules =


[buildozer]

# (int) Log level (0 = error only, 1 = warning, 2 = info, 3 = debug)
log_level = 2

# (int) Warn on root
warn_on_root = 1

# (str) Path to build artifact storage
# bin_dir = ./bin

# (str) Path to build output (i.e. .buildozer folder)
# build_dir = ./.buildozer

# (int) Buildozer will run in background or foreground
# 0 = background, 1 = foreground
# warn_on_root = 1
