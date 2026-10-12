"""Acoustic Messenger - send text between phones through sound waves."""
import threading
import time

import numpy as np
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import platform

import modem

SR = modem.SR


class AndroidAudio:
    """Playback and recording through Android's AudioTrack / AudioRecord."""

    def __init__(self):
        from jnius import autoclass
        self.AudioTrack = autoclass("android.media.AudioTrack")
        self.AudioRecord = autoclass("android.media.AudioRecord")
        self.AudioFormat = autoclass("android.media.AudioFormat")
        self.AudioManager = autoclass("android.media.AudioManager")
        self.rec = None

    def play(self, pcm: bytes):
        F = self.AudioFormat
        track = self.AudioTrack(self.AudioManager.STREAM_MUSIC, SR, F.CHANNEL_OUT_MONO,
                                F.ENCODING_PCM_16BIT, len(pcm), self.AudioTrack.MODE_STATIC)
        track.write(pcm, 0, len(pcm))
        track.play()
        time.sleep(len(pcm) / 2 / SR + 0.3)
        track.stop()
        track.release()

    def start_recording(self):
        F = self.AudioFormat
        minbuf = self.AudioRecord.getMinBufferSize(SR, F.CHANNEL_IN_MONO, F.ENCODING_PCM_16BIT)
        VOICE_RECOGNITION = 6  # least processing (no AGC / noise suppression on most phones)
        self.rec = self.AudioRecord(VOICE_RECOGNITION, SR, F.CHANNEL_IN_MONO,
                                    F.ENCODING_PCM_16BIT, max(minbuf, 8192) * 4)
        self.rec.startRecording()

    def read(self, nbytes=8192):
        buf = bytearray(nbytes)
        n = self.rec.read(buf, 0, nbytes)
        return bytes(buf[:max(n, 0)])

    def stop_recording(self):
        if self.rec:
            self.rec.stop()
            self.rec.release()
            self.rec = None


class DesktopAudio:
    """Desktop testing via the optional `sounddevice` package."""

    def __init__(self):
        import sounddevice as sd
        self.sd = sd
        self.stream = None

    def play(self, pcm: bytes):
        self.sd.play(modem.from_pcm16(pcm), SR)
        self.sd.wait()

    def start_recording(self):
        self.stream = self.sd.InputStream(samplerate=SR, channels=1, dtype="int16")
        self.stream.start()

    def read(self, nbytes=8192):
        data, _ = self.stream.read(nbytes // 2)
        return data.tobytes()

    def stop_recording(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None


class AcousticMessenger(App):
    title = "Acoustic Messenger"

    def build(self):
        Window.clearcolor = (0.07, 0.08, 0.11, 1)
        self.audio = None
        self.listening = False
        self.sending = False
        self.decoder = modem.Decoder()

        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        root.add_widget(Label(text="Acoustic Messenger", font_size="24sp", size_hint_y=None,
                              height=48, bold=True, color=(0.35, 0.8, 1, 1)))
        self.status = Label(text="Idle", size_hint_y=None, height=28, color=(0.7, 0.7, 0.7, 1))
        root.add_widget(self.status)

        self.log = Label(text="", markup=True, size_hint_y=None, halign="left", valign="top",
                         padding=(8, 8))
        self.log.bind(width=lambda *a: setattr(self.log, "text_size", (self.log.width, None)))
        self.log.bind(texture_size=lambda *a: setattr(self.log, "height", self.log.texture_size[1]))
        self.scroll = ScrollView()
        self.scroll.add_widget(self.log)
        root.add_widget(self.scroll)

        self.input = TextInput(hint_text="Type a message (max 64 bytes)", multiline=False,
                               size_hint_y=None, height=56, font_size="18sp")
        self.input.bind(on_text_validate=lambda *a: self.send())
        root.add_widget(self.input)

        row = BoxLayout(size_hint_y=None, height=60, spacing=8)
        self.send_btn = Button(text="Send", background_color=(0.1, 0.5, 0.9, 1))
        self.send_btn.bind(on_release=lambda *a: self.send())
        self.listen_btn = Button(text="Start listening", background_color=(0.1, 0.6, 0.4, 1))
        self.listen_btn.bind(on_release=lambda *a: self.toggle_listen())
        row.add_widget(self.send_btn)
        row.add_widget(self.listen_btn)
        root.add_widget(row)
        return root

    def on_start(self):
        if platform == "android":
            from android.permissions import Permission, request_permissions
            request_permissions([Permission.RECORD_AUDIO], lambda *a: self._init_audio())
        else:
            self._init_audio()

    def _init_audio(self, *a):
        try:
            self.audio = AndroidAudio() if platform == "android" else DesktopAudio()
            self.set_status("Ready")
        except Exception as e:  # noqa: BLE001
            self.set_status(f"Audio unavailable: {e}")

    # ---- UI helpers (safe from any thread)
    def set_status(self, text):
        Clock.schedule_once(lambda dt: setattr(self.status, "text", text))

    def add_log(self, who, text):
        stamp = time.strftime("%H:%M:%S")
        color = "66ccff" if who == "You" else "88ee88"

        def _do(dt):
            self.log.text += f"[color=888888]{stamp}[/color] [color={color}][b]{who}:[/b][/color] {text}\n"
            self.scroll.scroll_y = 0
        Clock.schedule_once(_do)

    # ---- sending
    def send(self):
        text = self.input.text.strip()
        if not text or self.sending or not self.audio:
            return
        self.input.text = ""
        threading.Thread(target=self._send_thread, args=(text,), daemon=True).start()

    def _send_thread(self, text):
        self.sending = True
        self.set_status("Transmitting...")
        try:
            pcm = modem.to_pcm16(modem.encode_message(text))
            self.audio.play(pcm)
            self.add_log("You", text)
        except Exception as e:  # noqa: BLE001
            self.set_status(f"Send failed: {e}")
        finally:
            self.decoder.reset()
            self.sending = False
            self.set_status("Listening..." if self.listening else "Ready")

    # ---- receiving
    def toggle_listen(self):
        if not self.audio:
            return
        if self.listening:
            self.listening = False
            self.listen_btn.text = "Start listening"
        else:
            self.listening = True
            self.listen_btn.text = "Stop listening"
            self.set_status("Listening...")
            threading.Thread(target=self._listen_thread, daemon=True).start()

    def _listen_thread(self):
        try:
            self.audio.start_recording()
            self.decoder.reset()
            while self.listening:
                raw = self.audio.read(8192)
                if self.sending or not raw:
                    continue
                for msg in self.decoder.feed(modem.from_pcm16(raw)):
                    self.add_log("Received", msg)
        except Exception as e:  # noqa: BLE001
            self.set_status(f"Mic error: {e}")
        finally:
            self.listening = False
            try:
                self.audio.stop_recording()
            except Exception:  # noqa: BLE001
                pass
            Clock.schedule_once(lambda dt: setattr(self.listen_btn, "text", "Start listening"))


if __name__ == "__main__":
    AcousticMessenger().run()
