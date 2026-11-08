# How Animal Homes Work: 3D Shorts

Original vertical (1080×1920) 3D animated Shorts that reveal animal homes through cutaways,
built with Blender's Python API and rendered locally. Free software only.

- `BRIEF.md`: channel direction, accuracy rules, visual signature
- `EPISODES.md`: episode concepts and the pilot recommendation
- `scripts/ep01_beaver_lodge.md`: beaver lodge script, fact-check table with sources, storyboard
- `scripts/ep02_polar_bear_den.md`: polar bear den script and sources (first fully produced episode)

## Making an episode end to end

```sh
# 1. Narration (scratch voice) -> audio + per-line timing
.venv-kokoro/bin/python tools/voiceover.py scripts/ep02_polar_bear_den.txt audio/narration/ep02_polar_bear_den.wav --voice am_michael --speed 1.08 --gap 0.3
#    or, with clips recorded elsewhere (ElevenLabs, your own voice), one file per script line:
python3 tools/import_lines.py scripts/ep02_polar_bear_den.txt audio/narration/ep02_clips/ audio/narration/ep02_polar_bear_den.wav --trim
# 2. Render (the scene reads the timing file, so animation follows the narration)
tools/render.sh blender/scenes/ep02_polar_bear_den.py preview    # ~10 min, check it
tools/render.sh blender/scenes/ep02_polar_bear_den.py final      # ~1 hour
# 3. Captions + mix + export
python3 tools/captions.py audio/narration/ep02_polar_bear_den.timing.json renders/ep02_polar_bear_den.ass --cues renders/ep02_polar_bear_den_cues.json
python3 tools/assemble.py exports/ep02_polar_bear_den_final.mp4 audio/narration/ep02_polar_bear_den.wav renders/ep02_polar_bear_den_cues.json renders/ep02_polar_bear_den.ass exports/ep02_polar_bear_den.mp4 --ambience-until 41
```

Sound effects are synthesized once with `tools/make_sfx.sh` (no licensing questions).

## Folders

| Folder | What goes in it |
| --- | --- |
| `blender/shorts/` | Reusable Python library: render setup (`core`), easing, path animation and narration timing (`anim`), camera rig, lights, materials, shapes, diorama blocks (`terrain`), sticks (`nature`), section cuts (`cutaway`), stand-in animals that walk, crouch and lie down (`creatures`), snowfall, glows, puffs and path highlights (`effects`). Environment look (v2 sample): heightfield terrain, rocks, sedge tufts, sea-ice ridges, cut faces and height images (`landscape`), procedural snow/snowpack/permafrost/rock/fur/ice materials plus haze and shader section clipping (`matlib`), shader-driven section cuts for whole landscapes (`section`), twilight sky and sun lamps (`atmosphere`), sculpted metaball polar bear (`bears`) |
| `blender/scenes/` | One script per video (or per shot). Each builds a scene from the library |
| `scripts/` | Narration scripts, fact-check notes, and shot lists, one file per video (copy `TEMPLATE.md`) |
| `references/` | Your screenshots or clips from reference channels (for studying style only) |
| `audio/narration`, `audio/sfx`, `audio/music` | Voice recordings or TTS output, sound effects, music (free/CC0 only) |
| `renders/` | Raw PNG frames and `.blend` files. Temporary: safe to delete |
| `previews/` | Low-res MP4s and contact sheets for review |
| `exports/` | Final 1080×1920 MP4s |
| `tools/` | Shell scripts that run Blender and ffmpeg |

## Installed tools

- **Blender 5.2.3 LTS** in `~/Applications/Blender.app` (installed by the agent, no admin needed)
- **ffmpeg 9.0** at `~/.local/bin/ffmpeg` (was already installed; supports H.264 and burned-in captions)
- **Kokoro** (free, local, Apache-2.0 licensed neural text-to-speech, smoother than Piper) in `.venv-kokoro/`. Model files are in `audio/voices/kokoro/`
- **Piper 1.8** (older, choppier option) in `.venv/`, with voice models in `audio/voices/`
- **macOS `say`** as a backup voice

## Commands

Run these from this folder in a terminal (Cursor: Terminal → New Terminal).

```sh
tools/render.sh blender/scenes/test_01_cutaway.py draft     # 270×480, fastest, for checking motion
tools/render.sh blender/scenes/test_01_cutaway.py preview   # 540×960, for review
tools/render.sh blender/scenes/test_01_cutaway.py final     # 1080×1920, goes to exports/
tools/render.sh blender/scenes/test_01_cutaway.py draft 150:150   # a single frame, no MP4
tools/contact_sheet.sh previews/test_01_cutaway_preview.mp4  # grid of 8 frames for quick review
tools/stills.sh blender/scenes/test_02_beaver_lodge.py draft 60 150 200   # a few frames side by side
.venv-kokoro/bin/python tools/voiceover.py scripts/ep01_beaver_lodge.txt audio/narration/ep01.wav --voice am_michael --speed 1.1
afplay audio/narration/ep01.wav                               # listen
```

`voiceover.py` (Kokoro) voices each script line separately and writes a `.timing.json` with when each line starts and ends. Captions and animation timing are built from it.
Voice samples to compare are in `audio/narration/samples/kokoro/` (Kokoro) and `audio/narration/samples/` (Piper, older).

To open a scene in Blender's interface and look around: open `renders/<scene name>.blend` (it's saved on every render).

## Workflow for each Short

1. **Topic and research.** Pick a question. Collect sources and fill in the fact-check table in `scripts/<video>.md` before writing anything visual.
2. **Script.** 110–150 words for 40–60 seconds. Hook in the first 2 seconds. Where it fits, structure it as "solving one problem reveals the next."
3. **Shot list.** Break the script into beats with timings, camera moves, and what each object does.
4. **Scene script.** Write `blender/scenes/<video>.py` with library components. Add new reusable pieces to `blender/shorts/`.
5. **Draft, then preview.** Iterate at draft quality until the timing works, then render a preview for review.
6. **Narration.** Record your voice, or generate it locally with TTS. Re-time the animation to the narration.
7. **Captions and sound.** Generate captions from the script and timings, add CC0 sound effects, and mix.
8. **Final render** at 1080×1920, then a final mux of video, audio, and captions into `exports/`.

## Rendering performance on this Mac (Apple M3, 16 GB)

Measured on the 8-second test scene with Blender's EEVEE engine (fast, GPU-based, game-engine-style rendering):

- Draft (270×480): ~75 s for 240 frames
- Preview (540×960): ~105 s for 240 frames (~0.4 s per frame)
- Final (1080×1920, 64 samples, motion blur): not yet measured. Expect several seconds per frame, so a 50-second Short could take 1–3 hours. Render overnight or lower the samples.

Cycles (Blender's slower, physically accurate path tracer) would be much slower on this laptop. EEVEE suits the clean, stylized look.

## Terms

- **EEVEE**: Blender's real-time render engine. Fast, good for stylized looks.
- **Boolean / cutaway**: subtracting one shape from another to show a cross-section.
- **Easing**: how motion speeds up and slows down. `ease_in_out` starts and stops gently. `ease_out_back` overshoots slightly, then settles.
- **Keyframe**: a value stored at a specific frame. Blender fills in the frames between keyframes.
- **Contact sheet**: one image tiling frames from a video so you can review it at a glance.
- **CRF**: video quality setting for H.264 encoding. Lower is higher quality (16–20 is visually lossless).
