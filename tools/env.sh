#!/bin/zsh
# Shared paths for the tools in this folder. Source it: `source tools/env.sh`

export SHORTS_ROOT="${0:A:h:h}"

if [[ -z "$BLENDER" ]]; then
  for candidate in \
    "$HOME/Applications/Blender.app/Contents/MacOS/Blender" \
    "/Applications/Blender.app/Contents/MacOS/Blender" \
    "$(command -v blender)"; do
    if [[ -x "$candidate" ]]; then export BLENDER="$candidate"; break; fi
  done
fi
[[ -x "$BLENDER" ]] || { echo "Blender not found. Install it to ~/Applications/Blender.app" >&2; return 1 2>/dev/null || exit 1; }
command -v ffmpeg >/dev/null || { echo "ffmpeg not found on PATH" >&2; return 1 2>/dev/null || exit 1; }
