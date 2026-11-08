"""Narration with Kokoro (free, local, Apache-2.0 licensed neural TTS).

Each non-empty line of the script file is synthesized separately, so we know
exactly when every line starts and ends. That timing drives captions and lets
scene scripts sync animation beats to the narration.

    .venv-kokoro/bin/python tools/voiceover.py <script.txt> <out.wav> [--voice am_michael] [--speed 1.0]
    .venv-kokoro/bin/python tools/voiceover.py --samples "Some text" audio/narration/samples/kokoro

Writes <out.wav> and <out>.timing.json: [{"text", "start", "end"}, ...] in seconds.
"""

import argparse
import json
import os
import sys

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MODEL_DIR = os.path.join(ROOT, "audio", "voices", "kokoro")
SAMPLE_VOICES = ["am_michael", "am_fenrir", "am_puck", "af_heart", "af_bella", "bm_george", "bf_emma"]


def load():
    return Kokoro(os.path.join(MODEL_DIR, "kokoro-v1.0.onnx"), os.path.join(MODEL_DIR, "voices-v1.0.bin"))


def synth(kokoro, text, voice, speed):
    lang = "en-gb" if voice.startswith("b") else "en-us"
    samples, rate = kokoro.create(text, voice=voice, speed=speed, lang=lang)
    return samples, rate


def voiceover(script, out, voice, speed, gap, lead_in):
    with open(script) as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.lstrip().startswith("#")]
    kokoro = load()
    chunks, timing, t, rate = [], [], lead_in, 24000
    for line in lines:
        samples, rate = synth(kokoro, line, voice, speed)
        timing.append({"text": line, "start": round(t, 3), "end": round(t + len(samples) / rate, 3)})
        chunks.append(samples)
        t += len(samples) / rate + gap
    silence = lambda s: np.zeros(int(s * rate), dtype=np.float32)
    audio = [silence(lead_in)]
    for c in chunks:
        audio += [c, silence(gap)]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    sf.write(out, np.concatenate(audio), rate)
    with open(os.path.splitext(out)[0] + ".timing.json", "w") as f:
        json.dump(timing, f, indent=1)
    print(f"Wrote {out} ({t:.1f}s, {len(lines)} lines)")


def samples(text, out_dir, speed):
    kokoro = load()
    os.makedirs(out_dir, exist_ok=True)
    for voice in SAMPLE_VOICES:
        audio, rate = synth(kokoro, text, voice, speed)
        path = os.path.join(out_dir, f"{voice}.wav")
        sf.write(path, audio, rate)
        print(f"Wrote {path} ({len(audio) / rate:.1f}s)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("script", nargs="?")
    p.add_argument("out")
    p.add_argument("--voice", default="am_michael")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--gap", type=float, default=0.35, help="seconds of silence between lines")
    p.add_argument("--lead-in", type=float, default=0.3)
    p.add_argument("--samples", metavar="TEXT", help="render TEXT in several voices into the out directory")
    a = p.parse_args()
    if a.samples:
        samples(a.samples, a.out, a.speed)
    elif a.script:
        voiceover(a.script, a.out, a.voice, a.speed, a.gap, a.lead_in)
    else:
        sys.exit("script file required")
