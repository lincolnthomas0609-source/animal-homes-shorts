"""Assemble separately recorded narration clips (ElevenLabs, your own voice, etc.).

Put one clip per script line in a folder, named so they sort in script order
(01.mp3, 02.mp3, ...). Any format ffmpeg reads works.

    python3 tools/import_lines.py <script.txt> <clips_dir> <out.wav> [--gap 0.35] [--lead-in 0.3] [--trim]

Writes <out.wav> and <out>.timing.json in the same format as voiceover.py, so
captions and animation timing work the same no matter where the voice came from.
--trim removes leading/trailing silence from each clip first.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".aiff"}


def duration(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", path])
    return float(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("script")
    p.add_argument("clips_dir")
    p.add_argument("out")
    p.add_argument("--gap", type=float, default=0.35)
    p.add_argument("--lead-in", type=float, default=0.3)
    p.add_argument("--trim", action="store_true")
    a = p.parse_args()

    with open(a.script) as f:
        lines = [ln.strip() for ln in f if ln.strip() and not ln.lstrip().startswith("#")]
    clips = sorted(os.path.join(a.clips_dir, c) for c in os.listdir(a.clips_dir)
                   if os.path.splitext(c)[1].lower() in AUDIO_EXT)
    if len(clips) != len(lines):
        sys.exit(f"{len(clips)} clips but {len(lines)} script lines. Need one clip per line.")

    with tempfile.TemporaryDirectory() as tmp:
        normalized = []
        for i, clip in enumerate(clips):
            dst = os.path.join(tmp, f"{i:03d}.wav")
            filters = ["aresample=48000"]
            if a.trim:
                filters += ["silenceremove=start_periods=1:start_threshold=-45dB",
                            "areverse", "silenceremove=start_periods=1:start_threshold=-45dB", "areverse"]
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-af", ",".join(filters),
                            "-ac", "1", dst], check=True)
            normalized.append(dst)

        timing, t, concat = [], a.lead_in, []
        silence = lambda s, name: (subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
             "-t", str(s), os.path.join(tmp, name)], check=True), os.path.join(tmp, name))[1]
        concat.append(silence(a.lead_in, "lead.wav"))
        gap = silence(a.gap, "gap.wav")
        for line, clip in zip(lines, normalized):
            d = duration(clip)
            timing.append({"text": line, "start": round(t, 3), "end": round(t + d, 3)})
            concat += [clip, gap]
            t += d + a.gap

        listing = os.path.join(tmp, "list.txt")
        with open(listing, "w") as f:
            f.writelines(f"file '{c}'\n" for c in concat)
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", listing,
                        "-c:a", "pcm_s16le", a.out], check=True)

    with open(os.path.splitext(a.out)[0] + ".timing.json", "w") as f:
        json.dump(timing, f, indent=1)
    print(f"Wrote {a.out} ({t:.1f}s, {len(lines)} lines)")


if __name__ == "__main__":
    main()
