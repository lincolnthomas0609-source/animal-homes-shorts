#!/bin/zsh
# Render a few individual frames and place them side by side, for fast checks.
# The scene is built once and each frame rendered in turn.
#
#   tools/stills.sh <scene.py> <draft|preview|final> <frame> [frame...]
#
# Output: previews/<scene>_stills.png
set -e
source "${0:A:h}/env.sh"
scene_file="${1:?scene}"; quality="${2:?quality}"; shift 2
name="${scene_file:t:r}"
dir="$SHORTS_ROOT/renders/${name}_stills"
rm -rf "$dir"
"$BLENDER" -b --factory-startup -P "$scene_file" -- --quality "$quality" --stills "${(j:,:)@}" --out "$dir" \
  2>&1 | grep -E "^\[shorts\]|Error|Traceback|^  File" || true
inputs=()
for f in "$@"; do
  inputs+=(-i "$dir/frame_$(printf %04d "$f").png")
done
out="$SHORTS_ROOT/previews/${name}_stills.png"
if (( $# > 1 )); then
  ffmpeg -hide_banner -loglevel error -y "${inputs[@]}" -filter_complex "hstack=inputs=$#" "$out"
else
  cp "$dir/frame_$(printf %04d "$1").png" "$out"
fi
echo "Wrote $out"
