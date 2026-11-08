# Handoff: continuing on the Windows PC

Written Nov 7, 2026, when work moved from the MacBook Air to the Windows gaming PC
(RTX 5080, 32 GB RAM). The Mac is too slow for rendering; **all rendering and video
assembly now happens on the PC.** Read this file first, then `README.md`, `BRIEF.md`
and `SETUP_WINDOWS.md`.

## The project in one paragraph

A YouTube Shorts channel called **How Animal Homes Work**: original vertical (1080×1920)
3D animated Shorts, 35–60 s, that reveal animal homes through cutaways and explain what
each part does. Everything is built from Python scripts that drive Blender 5.2.3 (EEVEE
engine), with ffmpeg for encoding, captions and the audio mix. Free, local tools only, no
paid services. Channel rules (accuracy, tone, no "animals designed/engineered") are in
`BRIEF.md`; episode ideas are in `EPISODES.md`.

## Where things stand

**Current episode: ep02, polar bear maternity den, "v2" look, about 35.8 s.**

- The user saw a short v2 look-dev sample (`previews/ep02_sample_v2_preview.mp4`) and said
  "that's exactly what I want it to look like". The full episode is now built in that style.
- Script: `scripts/ep02_polar_bear_den.txt`, 8 lines. Sources and the fact-check table are in
  `scripts/ep02_polar_bear_den.md` (old 12-line narration kept there as "v1").
- Narration: Kokoro scratch voice `am_michael` →
  `audio/narration/ep02_polar_bear_den.wav` plus `.timing.json` (narration ends at about
  34.4 s). It's a test voice; the user may switch to ElevenLabs or their own voice later
  (`tools/import_lines.py` imports one clip per script line).
- Scene: `blender/scenes/ep02_polar_bear_den_v2.py`. All 8 beats are built (the docstring
  at the top lists them): newborn cub close-up, pull back to the coastal tundra, autumn
  dig-in and snow seal, winter cutaway with body-heat glow, tunnel and air-hole highlight,
  cubs growing, spring breakout, family walking out with a distant male. The walking bear
  is `WalkingBear` in `blender/shorts/bears.py`.
- Sound cues and on-screen labels: `renders/ep02_polar_bear_den_v2_cues.json`
  (`duration` 35.8, `spring_start` 27.633). Captions: `renders/ep02_polar_bear_den_v2.ass`.
  Both are rewritten whenever the scene is built.

**Rendered so far:** one full 540×960 preview (`previews/ep02_polar_bear_den_v2_preview.mp4`,
video only, contact sheet `previews/ep02_polar_bear_den_v2_preview_sheet.png`). After
reviewing it, these fixes went into the scene file but have **not been rendered yet**:

1. Tunnel shot (about frames 440–740): the camera pulls back so the den room isn't cropped
   at the left edge.
2. Snow and breath puffs (about frames 270–370, also 700): fainter, so they read as wisps
   instead of solid white balls.
3. Final shot (about frames 820–1074): camera re-aimed so the walking family sits above the
   caption band instead of inside it.
4. The cubs' footstep sound cue moved one second later so it doesn't overlap the mother's.

**Not done yet:** the preview assembled with narration, sound and captions, and the
1080×1920 final render and export.

## Next steps on the PC

1. Set up the PC with `SETUP_WINDOWS.md` (Git LFS, Blender 5.2.3 exactly, ffmpeg,
   Python 3.11). Check with `python tools\shorts_env.py`.
2. Make sure the large files downloaded: `git lfs install` then `git lfs pull`. If
   `audio\narration\ep02_polar_bear_den.wav` is only about 130 bytes, it's an LFS pointer
   and the files haven't downloaded.
3. Render the preview again to check the four fixes:
   `python tools\render.py blender\scenes\ep02_polar_bear_den_v2.py preview`, then
   `python tools\contact_sheet.py previews\ep02_polar_bear_den_v2_preview.mp4`. Look at the
   sheet and at single frames around 560, 700, 905, 1000 and 1070.
4. Assemble that preview with sound and captions (same commands as step 5 of
   `SETUP_WINDOWS.md`, using the preview MP4 as input and
   `previews\ep02_polar_bear_den_v2_preview_full.mp4` as output) and show it to the user.
5. Once the user approves: time one final frame
   (`python tools\render.py blender\scenes\ep02_polar_bear_den_v2.py final 300:300`), then
   render the full final (about 1,074 frames) and assemble
   `exports\ep02_polar_bear_den_v2.mp4`. Verify it with ffprobe: 1080×1920, about 35.8 s,
   audio present.
6. Commit and push the scene changes (not the renders) to GitHub.

`exports/ep02_polar_bear_den.mp4` is the old 57-second v1 video. Leave it alone. The v1
scene `blender/scenes/ep02_polar_bear_den.py` expects the old 12-line narration, so it no
longer renders with the current timing file; don't use it.

## Lessons learned (avoid repeating these bugs)

- Blender 5.x removed `Action.fcurves`, so `blender/shorts/anim.py` bakes one keyframe per
  frame. Use `anim.tween`, `anim.key` and `anim.follow_path`, and build each property's
  animation in chronological order.
- Booleans: never put a section-cut plane exactly on a symmetry plane of the target (the
  v2 scene uses a shader section, `blender/shorts/section.py`, for the landscape). Bake
  static booleans with `shapes.bake`, and don't scale boolean targets to exactly 0 (use
  0.001). Use `shapes.shaft` for straight vertical tubes.
- Color: the AgX view transform desaturates bright colors; the look uses
  "AgX - Medium High Contrast".
- Composition: captions are burned in at roughly 60–72% of frame height and labels sit at
  the very top. Keep the den and the animals out of both areas.
- Scene files must stay portable: build paths from `core.ROOT` and never use absolute
  paths.
- `tools\render.py` deletes `renders\<scene>_<quality>\` before every run, even for a frame
  range, so a range render (`... final 300:300`) wipes the frames of an earlier full render.
  Time single frames before the full render, not after. On the PC, just re-render everything.
- Long renders: keep the PC from sleeping (for example
  `powercfg /change standby-timeout-ac 0` during the render, then set it back).

## Science rules for this episode

One room (about 2 × 1.5 × 1 m), an entrance tunnel about 2 m long that rises toward the
room so warm air stays in, the entrance sealed by snow, **one** small air hole, cubs about
0.5 kg and about 30–35 cm at birth, born Dec/Jan. Only pregnant females den for the
winter. No extra rooms, vents or furnishings. Animals and sizes are labeled "Illustrative,
not to scale" whenever the den is cut open.

## Accounts and repos

- GitHub (main repo, used by both machines):
  https://github.com/lincolnthomas0609-source/animal-homes-shorts. The account is
  `lincolnthomas0609-source`, with "-source" at the end. "Page not found" in the browser
  means the browser isn't signed in as that account.
- Cursor uses the user's school account (`lincoln.thomas@alpha.school`).
- A second remote `cursor` (`trilogy-cursor-central-account/render-kit` on Cursor's git
  host) was requested but the push was refused (403) because the Mac's `origin` CLI is
  signed in as the Gmail account. It's optional; GitHub is enough for moving the project.
  See `REPO_SYNC.md`.

## Working with the user

The user is new to terminals and git. Give click-by-click steps in plain language, run
commands yourself when you can, and say clearly when they need to click "Yes" on a Windows
prompt or sign in somewhere. They care about how long things take, so give time estimates
for renders. Don't render or assemble anything on the Mac anymore.
