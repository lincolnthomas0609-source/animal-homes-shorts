"""Encode a folder of frame_0001.png... into an H.264 MP4 that YouTube accepts.

    python tools/encode.py <frames_dir> <out.mp4> [crf] [fps]

Cross-platform version of tools/encode.sh.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shorts_env import ffmpeg, ffprobe  # noqa: E402


def encode(frames_dir, out, crf=18, fps=30):
    frames_dir = Path(frames_dir)
    frames = sorted(frames_dir.glob("frame_*.png"))
    if not frames:
        sys.exit(f"No frame_*.png files in {frames_dir}")
    digits = frames[0].stem[len("frame_"):]
    start_number = int(digits) if digits.isdigit() else 0

    subprocess.run([
        ffmpeg(), "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", str(fps), "-start_number", str(start_number), "-i", str(frames_dir / "frame_%04d.png"),
        "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(out),
    ], check=True)
    info = subprocess.run([
        ffprobe(), "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,nb_frames", "-of", "csv=p=0", str(out),
    ], capture_output=True, text=True).stdout.strip()
    print(f"Wrote {out} ({info})")


def main(argv):
    if len(argv) < 2:
        sys.exit("usage: python tools/encode.py <frames_dir> <out.mp4> [crf] [fps]")
    crf = argv[2] if len(argv) > 2 else 18
    fps = argv[3] if len(argv) > 3 else 30
    encode(argv[0], argv[1], crf, fps)


if __name__ == "__main__":
    main(sys.argv[1:])
