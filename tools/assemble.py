"""Mix narration, ambience, and sound-effect cues, burn in captions, and export the final MP4.

    python3 tools/assemble.py <video.mp4> <narration.wav> <cues.json> <captions.ass> <out.mp4>
        [--ambience wind] [--ambience-db -22] [--ambience-until 41.0]

cues.json (written by the scene script): {"duration": s, "cues": [{"name", "time", "gain"}], "labels": [...]}.
Each cue name is a file in audio/sfx/<name>.wav (see tools/make_sfx.sh).
"""

import argparse
import json
import os
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FONTS = os.path.join(ROOT, "assets", "fonts")
if not os.path.isdir(FONTS):
    FONTS = "/System/Library/Fonts/Supplemental"


def filter_path(path):
    return path.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("video")
    p.add_argument("narration")
    p.add_argument("cues")
    p.add_argument("captions")
    p.add_argument("out")
    p.add_argument("--ambience", default="wind")
    p.add_argument("--ambience-db", type=float, default=-22)
    p.add_argument("--ambience-until", type=float, help="fade the ambience out by this time (s)")
    p.add_argument("--sfx-db", type=float, default=-8, help="overall sound effect level")
    a = p.parse_args()

    with open(a.cues) as f:
        data = json.load(f)
    duration = data["duration"]
    sfx_dir = os.path.join(ROOT, "audio", "sfx")

    inputs = ["-i", a.video, "-i", a.narration]
    filters = ["[1:a]aresample=48000,aformat=channel_layouts=mono,volume=0dB[narr]"]
    mix = ["[narr]"]
    idx = 2
    if a.ambience:
        inputs += ["-i", os.path.join(sfx_dir, f"{a.ambience}.wav")]
        until = a.ambience_until or duration
        filters.append(f"[{idx}:a]atrim=0:{duration},volume={a.ambience_db}dB,"
                       f"afade=t=in:d=1.5,afade=t=out:st={max(until - 2.0, 0)}:d=2.0[amb]")
        mix.append("[amb]")
        idx += 1
    for i, c in enumerate(data["cues"]):
        inputs += ["-i", os.path.join(sfx_dir, f"{c['name']}.wav")]
        ms = int(c["time"] * 1000)
        filters.append(f"[{idx}:a]adelay={ms}|{ms},volume={a.sfx_db + c.get('gain', 0)}dB[s{i}]")
        mix.append(f"[s{i}]")
        idx += 1
    # YouTube plays everything back at about -14 LUFS and only turns loud videos down,
    # so normalize to that loudness (true peak -1.5 dB) rather than leaving the mix quiet.
    filters.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=longest,"
                   f"atrim=0:{duration},loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000,"
                   f"aformat=channel_layouts=stereo[aout]")
    filters.append(f"[0:v]subtitles='{filter_path(a.captions)}':fontsdir='{filter_path(FONTS)}'[vout]")

    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
           "-filter_complex", ";".join(filters), "-map", "[vout]", "-map", "[aout]",
           "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(duration), a.out]
    subprocess.run(cmd, check=True)
    print(f"Wrote {a.out}")


if __name__ == "__main__":
    main()
