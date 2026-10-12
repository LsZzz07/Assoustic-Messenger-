"""Acoustic Messenger modem: text <-> audio using 16-tone FSK (4 bits/symbol).

Frame = PREAMBLE symbols + [len][payload...][crc16 hi][crc16 lo] (as nibbles).
Tones sit in the audible 1.5-5.2 kHz band, which phone speakers and mics handle well.
Throughput is ~6 bytes/second; a 20 character message takes about 5 seconds.
"""
import numpy as np

SR = 44100
N = 3528                     # samples per symbol (80 ms)
BASE = 1500.0                # Hz, tone 0
SPACING = 250.0              # Hz between tones (multiple of 1/0.08s = 12.5 Hz -> orthogonal)
NTONES = 16
PREAMBLE = [0, 15] * 4 + [3, 12]
MAX_PAYLOAD = 64

_t = np.arange(N) / SR
_freqs = BASE + SPACING * np.arange(NTONES)
_REF = np.exp(-2j * np.pi * _freqs[:, None] * _t[None, :]).astype(np.complex64)
_ENV = np.ones(N, dtype=np.float32)
_ramp = np.linspace(0, 1, 220, dtype=np.float32)
_ENV[:220] = _ramp
_ENV[-220:] = _ramp[::-1]


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def _to_symbols(data: bytes):
    out = []
    for b in data:
        out += [b >> 4, b & 15]
    return out


def build_frame(text: str):
    payload = text.encode("utf-8")[:MAX_PAYLOAD]
    body = bytes([len(payload)]) + payload
    c = crc16(body)
    body += bytes([c >> 8, c & 255])
    return PREAMBLE + _to_symbols(body)


def synthesize(symbols, amp=0.8):
    out = np.zeros((len(symbols) + 4) * N, dtype=np.float32)
    for i, s in enumerate(symbols):
        out[(i + 2) * N:(i + 3) * N] = np.sin(2 * np.pi * _freqs[s] * _t) * _ENV
    return amp * out


def encode_message(text: str) -> np.ndarray:
    """Return float32 mono audio (SR Hz) carrying the text."""
    return synthesize(build_frame(text))


def to_pcm16(audio: np.ndarray) -> bytes:
    return (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()


def from_pcm16(raw: bytes) -> np.ndarray:
    return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0


def _symbol_at(x, pos):
    e = np.abs(_REF @ x[pos:pos + N])
    return int(np.argmax(e))


def _preamble_ok(x, pos):
    if np.sqrt(np.mean(x[pos:pos + N] ** 2)) < 0.004:
        return False
    for i, s in enumerate(PREAMBLE):
        if _symbol_at(x, pos + i * N) != s:
            return False
    return True


def _read_bytes(x, start, count):
    if start + count * 2 * N > len(x):
        return None
    syms = [_symbol_at(x, start + i * N) for i in range(count * 2)]
    return bytes((syms[i] << 4) | syms[i + 1] for i in range(0, len(syms), 2))


def decode(x):
    """Scan audio for frames. Returns (messages, keep_from_index)."""
    x = np.asarray(x, dtype=np.float32)
    msgs, pos, step = [], 0, N // 8
    plen = len(PREAMBLE) * N
    while pos + plen + N <= len(x):
        if not _preamble_ok(x, pos):
            pos += step
            continue
        good = [o for o in range(pos, pos + N // 4, N // 32)
                if o + plen + N <= len(x) and _preamble_ok(x, o)]
        start = good[len(good) // 2] + plen
        head = _read_bytes(x, start, 1)
        if head is None:
            break
        n = head[0]
        if n > MAX_PAYLOAD:
            pos += plen
            continue
        body = _read_bytes(x, start, n + 3)
        if body is None:
            break                      # frame not fully recorded yet
        if crc16(body[:-2]) == (body[-2] << 8 | body[-1]):
            msgs.append(body[1:-2].decode("utf-8", errors="replace"))
            pos = start + (n + 3) * 2 * N
        else:
            pos += plen
    return msgs, pos


class Decoder:
    """Feed it microphone chunks; get decoded messages back."""

    def __init__(self, max_seconds=40):
        self.buf = np.zeros(0, dtype=np.float32)
        self.max = max_seconds * SR

    def feed(self, chunk):
        self.buf = np.concatenate([self.buf, np.asarray(chunk, dtype=np.float32)])
        msgs, keep = decode(self.buf)
        self.buf = self.buf[keep:][-self.max:]
        return msgs

    def reset(self):
        self.buf = np.zeros(0, dtype=np.float32)


if __name__ == "__main__":
    import sys
    import wave
    text = " ".join(sys.argv[1:]) or "Hello from Acoustic Messenger"
    audio = encode_message(text)
    with wave.open("message.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(to_pcm16(audio))
    print(f"Wrote message.wav ({len(audio) / SR:.1f}s) - play it near another device running the app.")
