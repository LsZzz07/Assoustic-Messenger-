[app]
title = Acoustic Messenger
package.name = acousticmessenger
package.domain = org.acoustic
source.dir = .
source.include_exts = py
source.exclude_patterns = test_modem.py
version = 1.0
requirements = python3,kivy==2.3.0,numpy,pyjnius,android
orientation = portrait
fullscreen = 0
android.permissions = RECORD_AUDIO,MODIFY_AUDIO_SETTINGS
android.api = 33
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
