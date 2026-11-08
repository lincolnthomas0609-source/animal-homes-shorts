"""Tile evenly spaced frames from a video into one image for quick review.

    python tools/contact_sheet.py <video.mp4> [out.png] [count]

Cross-platform version of tools/contact_sheet.sh.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shorts_env import BUNDLED_FONT, WINDOWS, ffmpeg, ffprobe, filter_path  # noqa: E402


def contact_sheet(video, out=None, count=8):
    video = Path(video)
    out = Path(out) if out else video.with_name(video.stem + "_sheet.png")
    total = int(subprocess.run([
        ffprobe(), "-v", "error", "-select_streams", "v:0", "-count_packets",
        "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(video),
    ], capture_output=True, text=True, check=True).stdout.strip())
    step = max(total // count, 1)
    cols = min(count, 4)
    rows = (count + cols - 1) // cols

    # ffmpeg on Windows often has no default font configured, so point drawtext at the bundled one.
    font = f"fontfile={filter_path(BUNDLED_FONT)}:" if WINDOWS and BUNDLED_FONT.is_file() else ""
    vf = (rf"select='not(mod(n\,{step}))',scale=270:-2,"
          rf"drawtext={font}text='%{{pts\:hms}}':x=8:y=8:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.5,"
          rf"tile={cols}x{rows}:padding=4")
    proc = subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(video),
                           "-vf", vf, "-fps_mode", "vfr", "-frames:v", "1", str(out)],
                          stderr=subprocess.PIPE, text=True, errors="replace")
    for line in proc.stderr.splitlines():
        if "Fontconfig" not in line:
            print(line, file=sys.stderr)
    if proc.returncode:
        sys.exit(proc.returncode)
    print(f"Wrote {out}")


def main(argv):
    if not argv:
        sys.exit("usage: python tools/contact_sheet.py <video.mp4> [out.png] [count]")
    contact_sheet(argv[0], argv[1] if len(argv) > 1 else None, int(argv[2]) if len(argv) > 2 else 8)


if __name__ == "__main__":
    main(sys.argv[1:])
