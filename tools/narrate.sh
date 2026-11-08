#!/bin/zsh
# Generate narration locally with Piper (free neural text-to-speech).
#
#   tools/narrate.sh <script.txt> <out.wav> [voice] [speed]
#
# voice: a model name in audio/voices/ (default en_US-ryan-high).
#        Download more with: .venv/bin/python -m piper.download_voices --download-dir audio/voices <name>
#        Browse voices at https://rhasspy.github.io/piper-samples/
# speed: >1 is faster, <1 is slower (default 1.05).
set -e
root="${0:A:h:h}"
text="${1:?text file}"
out="${2:?output wav}"
voice="${3:-en_US-ryan-high}"
speed="${4:-1.05}"
length_scale=$(echo "1 / $speed" | bc -l)

mkdir -p "${out:h}"
"$root/.venv/bin/python" -m piper \
  -m "$root/audio/voices/$voice.onnx" \
  -i "$text" -f "$out" \
  --length-scale "$length_scale" --sentence-silence 0.25
printf "Wrote %s (%.1fs)\n" "$out" "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$out")"
