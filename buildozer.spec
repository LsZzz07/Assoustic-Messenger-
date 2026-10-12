[app]
title = Acoustic Messenger
package.name = acousticmessenger
package.domain = org.acoustic

source.dir = .
source.include_exts = py
source.exclude_patterns = test_modem.py

version = 1.0

# Pinned versions: the unpinned "python3" pulled a Python too new for Kivy 2.3.0
requirements = python3==3.11.5,hostpython3==3.11.5,kivy==2.3.0,numpy,pyjnius,android

orientation = portrait
fullscreen = 0

android.permissions = RECORD_AUDIO,MODIFY_AUDIO_SETTINGS
android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

# Stable python-for-android release that works with Python 3.11 + Kivy 2.3.0
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
