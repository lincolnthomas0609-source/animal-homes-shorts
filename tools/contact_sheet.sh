#!/bin/zsh
# Tile evenly spaced frames from a video into one image for quick review.
#
#   tools/contact_sheet.sh <video.mp4> [out.png] [count]
set -e
video="${1:?video}"
out="${2:-${video:r}_sheet.png}"
count="${3:-8}"
total=$(ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "$video")
step=$(( total / count ))
cols=$(( count < 4 ? count : 4 ))
rows=$(( (count + cols - 1) / cols ))

ffmpeg -hide_banner -loglevel error -y -i "$video" \
  -vf "select='not(mod(n\,$step))',scale=270:-2,drawtext=text='%{pts\:hms}':x=8:y=8:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.5,tile=${cols}x${rows}:padding=4" \
  -fps_mode vfr -frames:v 1 "$out" 2> >(grep -v Fontconfig >&2)
echo "Wrote $out"
