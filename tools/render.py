"""Build a scene, render its frames headless, and encode an MP4.

    python tools/render.py <scene.py> [draft|preview|final] [start:end]

draft = 270x480, preview = 540x960, final = 1080x1920.
Draft and preview MP4s go to previews/, final MP4s to exports/.
Passing start:end renders only those frames (no MP4), e.g. 150:150 for one still.

Cross-platform version of tools/render.sh.
"""

import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from encode import encode  # noqa: E402
from shorts_env import ROOT, blender, ffmpeg, run_blender  # noqa: E402

USAGE = "usage: python tools/render.py <scene.py> [draft|preview|final] [start:end]"
QUALITIES = ("draft", "preview", "final")
KEEP = re.compile(r"^\[shorts\]|Error|Traceback|^  File|Saved:")
DROP = re.compile(r"Saved: '.*frame_")


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        sys.exit(USAGE)
    scene_file = Path(argv[0])
    quality = argv[1] if len(argv) > 1 else "preview"
    frames = argv[2] if len(argv) > 2 else ""
    if quality not in QUALITIES:
        sys.exit(f"quality must be one of {', '.join(QUALITIES)}\n{USAGE}")
    if frames and not re.fullmatch(r"\d+:\d+", frames):
        sys.exit(f"frame range must look like 150:150 or 1:240\n{USAGE}")
    if not scene_file.is_file():
        sys.exit(f"Scene not found: {scene_file}")

    name = scene_file.stem
    frames_dir = ROOT / "renders" / f"{name}_{quality}"
    extra = ["--frames", frames] if frames else []
    blender(), ffmpeg()  # exit before deleting old frames if a tool is missing

    shutil.rmtree(frames_dir, ignore_errors=True)
    start = time.time()
    run_blender(["-b", "--factory-startup", "-P", str(scene_file.resolve()), "--",
                 "--quality", quality, "--render", *extra],
                keep=lambda line: KEEP.search(line) and not DROP.search(line))
    print(f"Rendered in {int(time.time() - start)}s -> {frames_dir}")

    if not list(frames_dir.glob("frame_*.png")):
        sys.exit("No frames rendered")
    if frames:
        return

    if quality == "final":
        out_dir, crf = ROOT / "exports", 16
    else:
        out_dir, crf = ROOT / "previews", 20
    out_dir.mkdir(parents=True, exist_ok=True)
    encode(frames_dir, out_dir / f"{name}_{quality}.mp4", crf)


if __name__ == "__main__":
    main(sys.argv[1:])
