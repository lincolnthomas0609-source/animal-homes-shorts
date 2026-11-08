#!/bin/zsh
# Build a scene, render its frames headless, and encode an MP4.
#
#   tools/render.sh <scene.py> [draft|preview|final] [start:end]
#
# draft = 270x480, preview = 540x960, final = 1080x1920.
# Draft and preview MP4s go to previews/, final MP4s to exports/.
# Passing start:end renders only those frames (no MP4), e.g. 150:150 for one still.
set -e
source "${0:A:h}/env.sh"

scene_file="${1:?usage: tools/render.sh <scene.py> [draft|preview|final] [start:end]}"
quality="${2:-preview}"
frames="$3"
name="${scene_file:t:r}"
frames_dir="$SHORTS_ROOT/renders/${name}_${quality}"

extra=()
[[ -n "$frames" ]] && extra=(--frames "$frames")

rm -rf "$frames_dir"
start=$(date +%s)
"$BLENDER" -b --factory-startup -P "$scene_file" -- --quality "$quality" --render "${extra[@]}" \
  2>&1 | grep -E "^\[shorts\]|Error|Traceback|^  File|Saved:" | grep -v "Saved: '.*frame_" || true
echo "Rendered in $(( $(date +%s) - start ))s -> $frames_dir"

ls "$frames_dir"/frame_*.png >/dev/null 2>&1 || { echo "No frames rendered" >&2; exit 1; }
[[ -n "$frames" ]] && exit 0

if [[ "$quality" == "final" ]]; then out_dir="$SHORTS_ROOT/exports"; crf=16; else out_dir="$SHORTS_ROOT/previews"; crf=20; fi
mkdir -p "$out_dir"
out="$out_dir/${name}_${quality}.mp4"
"$SHORTS_ROOT/tools/encode.sh" "$frames_dir" "$out" "$crf"
