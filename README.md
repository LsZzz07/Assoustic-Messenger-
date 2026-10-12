# Acoustic Messenger

Send short text messages between phones using sound waves (16-tone FSK, 1.5-5.2 kHz, ~6 bytes/s).
Messages carry a CRC-16, so corrupted audio is rejected instead of showing garbage.

## Get the APK (pick one)
**A. GitHub (no local setup):** create a repo, upload this folder, open the *Actions* tab ->
*Build APK* -> download the `AcousticMessenger-apk` artifact when it finishes.

**B. Ubuntu / WSL2:** `./build_apk.sh` -> APK appears in `bin/`.

Install on Android: copy the APK to the phone, allow "install unknown apps", tap it.

## Use
Open the app on two phones, tap **Start listening** on one, type a message on the other and tap **Send**.
Keep phones 0.5-2 m apart in a fairly quiet room, volume at ~70%+. Half-duplex: one talks at a time.

## Test without a phone
    python modem.py "hello"      # writes message.wav
    python test_modem.py         # noise/offset self-test
