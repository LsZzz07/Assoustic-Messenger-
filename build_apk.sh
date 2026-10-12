#!/usr/bin/env bash
# Build the APK on Ubuntu/Debian (or WSL2 on Windows). Takes ~20-40 min the first time.
set -e
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip python3-venv autoconf libtool \
  pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo6 cmake libffi-dev libssl-dev
python3 -m venv .venv && source .venv/bin/activate
pip install --upgrade pip buildozer cython==0.29.36
buildozer -v android debug
echo "Done -> bin/*.apk"
