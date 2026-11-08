#!/bin/zsh
# Side-by-side BEFORE/AFTER comparison of matching frames from two frame folders.
#
#   tools/before_after.sh <before_dir> <after_dir> <out.png> <frame> [frame...]
#
# Top row BEFORE, bottom row AFTER, one column per frame (frame_####.png in each folder).
set -e
before="${1:?before dir}"; after="${2:?after dir}"; out="${3:?out.png}"; shift 3
w=432; h=768
inputs=(); filters=""; n=0
for f in "$@"; do
  name="frame_$(printf %04d "$f").png"
  inputs+=(-i "$before/$name" -i "$after/$name")
  for side in BEFORE AFTER; do
    filters+="[$n:v]scale=$w:$h,drawtext=text='$side  (frame $f)':x=12:y=12:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=6[v$n];"
    n=$(( n + 1 ))
  done
done
cols=$#
layout=""
for (( i = 0; i < cols; i++ )); do layout+="$(( i * w ))_0|"; done
for (( i = 0; i < cols; i++ )); do layout+="$(( i * w ))_$h|"; done
order=""
for (( i = 0; i < cols; i++ )); do order+="[v$(( 2 * i ))]"; done
for (( i = 0; i < cols; i++ )); do order+="[v$(( 2 * i + 1 ))]"; done
ffmpeg -hide_banner -loglevel error -y "${inputs[@]}" \
  -filter_complex "${filters}${order}xstack=inputs=$(( 2 * cols )):layout=${layout%|}:fill=black" \
  "$out" 2> >(grep -v Fontconfig >&2)
echo "Wrote $out"
