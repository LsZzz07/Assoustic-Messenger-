import numpy as np, modem
rng = np.random.default_rng(1)
def trial(text, snr_db, offset, chunked=True):
    a = modem.encode_message(text) * rng.uniform(0.1, 0.6)
    sig_p = np.mean(a[a != 0] ** 2)
    noise = rng.normal(0, np.sqrt(sig_p / 10 ** (snr_db / 10)), len(a) + offset + 30000)
    x = noise.copy(); x[offset:offset + len(a)] += a
    d = modem.Decoder(); out = []
    step = 4096 if chunked else len(x)
    for i in range(0, len(x), step):
        out += d.feed(x[i:i + step])
    return out
ok = 0; tot = 0
for snr in (20, 10, 5, 0):
    for off in (0, 1234, 20000, 33333):
        for t in ("Hi", "Hello from Acoustic Messenger!", "Ünïcode ✓ test"):
            tot += 1; r = trial(t, snr, off)
            ok += r == [t]
    print("snr", snr, "cumulative", ok, "/", tot)
