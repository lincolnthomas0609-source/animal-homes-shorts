"""Render a few individual frames and place them side by side, for fast checks.
The scene is built once and each frame rendered in turn.

    python tools/stills.py <scene.py> <draft|preview|final> <frame> [frame...]

Output: previews/<scene>_stills.png

Cross-platform version of tools/stills.sh.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shorts_env import ROOT, blender, ffmpeg, run_blender  # noqa: E402

USAGE = "usage: python tools/stills.py <scene.py> <draft|preview|final> <frame> [frame...]"
KEEP = re.compile(r"^\[shorts\]|Error|Traceback|^  File")


def main(argv):
    if len(argv) < 3:
        sys.exit(USAGE)
    scene_file, quality, frames = Path(argv[0]), argv[1], argv[2:]
    if quality not in ("draft", "preview", "final"):
        sys.exit(USAGE)
    if not all(f.isdigit() for f in frames):
        sys.exit(f"frames must be numbers\n{USAGE}")
    if not scene_file.is_file():
        sys.exit(f"Scene not found: {scene_file}")

    name = scene_file.stem
    out_dir = ROOT / "renders" / f"{name}_stills"
    blender(), ffmpeg()  # exit before deleting old stills if a tool is missing
    shutil.rmtree(out_dir, ignore_errors=True)
    run_blender(["-b", "--factory-startup", "-P", str(scene_file.resolve()), "--",
                 "--quality", quality, "--stills", ",".join(frames), "--out", str(out_dir)],
                keep=lambda line: KEEP.search(line))

    pngs = [out_dir / f"frame_{int(f):04d}.png" for f in frames]
    missing = [p.name for p in pngs if not p.is_file()]
    if missing:
        sys.exit(f"Not rendered: {', '.join(missing)}")
    out = ROOT / "previews" / f"{name}_stills.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    if len(pngs) > 1:
        inputs = [arg for p in pngs for arg in ("-i", str(p))]
        subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", *inputs,
                        "-filter_complex", f"hstack=inputs={len(pngs)}", str(out)], check=True)
    else:
        shutil.copyfile(pngs[0], out)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
