# Rendering on the Windows PC

Steps to set up a Windows gaming PC (here an RTX 5080) to render and assemble episodes.
The Mac keeps working as before; both machines share the project through the
Cursor-hosted git repo.

Type the commands below in **PowerShell** or in Cursor's terminal (Terminal → New Terminal),
inside the project folder unless a step says otherwise.

## 1. Get the project onto the PC

Install Git first: `winget install Git.Git`, then close and reopen the terminal.
Tell git who you are (once per PC):

```powershell
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

The `origin` command-line tool that signs git in to Cursor-hosted repos only runs on macOS
and Linux, so the reliable way to clone on Windows is an SSH key:

1. On the PC, make a key (press Enter at every question):
   ```powershell
   ssh-keygen -t ed25519 -C "gaming-pc"
   Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
   ```
   Copy the one line it prints (starts with `ssh-ed25519`). It's the public half and safe to share.
2. On the Mac, save that line to a file such as `~/pc_key.pub` and register it:
   ```sh
   origin ssh-key add --title "Gaming PC" --key-file ~/pc_key.pub
   ```
3. On the PC, clone with the **SSH** clone URL from the repo page
   (`https://cursor.com/codebase/<org>/animal-homes-shorts`, see the README):
   ```powershell
   cd $env:USERPROFILE\Documents
   git clone <SSH clone URL> animal-homes-shorts
   ```
4. In Cursor: File → Open Folder → `Documents\animal-homes-shorts`.

You can also try Cursor's own **Clone Repo** button (on the start screen, or Ctrl+Shift+P →
"Git: Clone") with the HTTPS clone URL. If it asks for a password, use the SSH steps above.

## 2. Install Blender, ffmpeg and Python

**Blender 5.2.3 LTS** (use exactly this version; scenes are written for it):
download the Windows installer (`blender-5.2.3-windows-x64.msi`) from
<https://www.blender.org/download/release/Blender5.2/> and install with the default options.
It goes to `C:\Program Files\Blender Foundation\Blender 5.2\`, where the tools look for it.
If you install somewhere else, set `BLENDER` to the full path of `blender.exe`:
`setx BLENDER "D:\Blender\blender.exe"` (then reopen the terminal).

**ffmpeg** (any recent static build). Pick one option:

- Easiest: `winget install Gyan.FFmpeg`
- Or manually: download `ffmpeg-release-full.7z` from <https://www.gyan.dev/ffmpeg/builds/>,
  extract it, rename the folder to `C:\ffmpeg` (so `C:\ffmpeg\bin\ffmpeg.exe` exists), then add
  `C:\ffmpeg\bin` to PATH: Start → "Edit the system environment variables" → Environment
  Variables → under *User variables* select `Path` → Edit → New → `C:\ffmpeg\bin` → OK.
- Or copy `ffmpeg.exe` and `ffprobe.exe` into `tools\bin\` in the project. That folder is
  git-ignored. Only the new Python tools look there; `assemble.py` and `import_lines.py`
  need ffmpeg on PATH, so prefer one of the options above.

**Python 3.11**: `winget install Python.Python.3.11`, or the installer from
<https://www.python.org/downloads/> (tick **"Add python.exe to PATH"**).
If typing `python` opens the Microsoft Store, use `py` instead of `python` in every command below.

Close and reopen the terminal, then check that everything is found:

```powershell
python tools\shorts_env.py
```

It prints the Blender, ffmpeg and ffprobe paths and the Blender version (should say 5.2.3).

## 3. Optional: Kokoro voice (only for new narration)

The narration audio and its timing files are already in the repo
(`audio\narration\*.wav` and `*.timing.json`), so you only need this to generate new narration.

```powershell
py -3.11 -m venv .venv-kokoro
.venv-kokoro\Scripts\pip install kokoro-onnx soundfile
```

Download the two model files into `audio\voices\kokoro\` (they're too big for git):

- <https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx>
- <https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin>

Then, for example:

```powershell
.venv-kokoro\Scripts\python tools\voiceover.py scripts\ep02_polar_bear_den.txt audio\narration\ep02_polar_bear_den.wav --voice am_michael --speed 1.08 --gap 0.3
```

## 4. GPU

Nothing to configure: EEVEE (the render engine the scenes use) renders on the graphics card
automatically. Do update the NVIDIA driver first (NVIDIA App, or <https://www.nvidia.com/drivers>;
the Game Ready or Studio driver both work). RTX 50-series cards need a recent driver.

## 5. Render and assemble

The zsh scripts in `tools\*.sh` are Mac-only. Use the Python versions, which take the same
arguments and write the same files:

| Mac | Windows (and Mac) |
| --- | --- |
| `tools/render.sh` | `python tools\render.py` |
| `tools/stills.sh` | `python tools\stills.py` |
| `tools/contact_sheet.sh` | `python tools\contact_sheet.py` |
| `tools/encode.sh` | `python tools\encode.py` |
| `tools/make_sfx.sh` | `python tools\make_sfx.py` |

First, a quick test with the small test scene (a few seconds):

```powershell
python tools\render.py blender\scenes\test_01_cutaway.py draft 1:1
```

**Time one final frame** before committing to a full render. This renders frame 300 at full
quality and prints how long it took. It also clears `renders\ep02_polar_bear_den_v2_final\`,
so do it *before* the full render, not after.

```powershell
python tools\render.py blender\scenes\ep02_polar_bear_den_v2.py final 300:300
```

Multiply the seconds by the number of frames to estimate the full render: frames = the
`duration` in `renders\ep02_polar_bear_den_v2_cues.json` × 30 (about 1,050 frames for 35 s).

Then the episode end to end (same steps as the README's "Making an episode end to end"):

```powershell
# 1. Render (preview to check, then final -> exports\ep02_polar_bear_den_v2_final.mp4)
python tools\render.py blender\scenes\ep02_polar_bear_den_v2.py preview
python tools\render.py blender\scenes\ep02_polar_bear_den_v2.py final

# 2. Captions from the narration timing and the scene's labels
python tools\captions.py audio\narration\ep02_polar_bear_den.timing.json renders\ep02_polar_bear_den_v2.ass --cues renders\ep02_polar_bear_den_v2_cues.json

# 3. Mix narration + sound effects, burn in captions, export
#    The wind ambience fades out when spring starts; the first line reads that time from the cues file.
$spring = python -c "import json; print(json.load(open('renders/ep02_polar_bear_den_v2_cues.json'))['spring_start'])"
python tools\assemble.py exports\ep02_polar_bear_den_v2_final.mp4 audio\narration\ep02_polar_bear_den.wav renders\ep02_polar_bear_den_v2_cues.json renders\ep02_polar_bear_den_v2.ass exports\ep02_polar_bear_den_v2.mp4 --ambience-until $spring
```

The finished Short is `exports\ep02_polar_bear_den_v2.mp4`.

Captions use the bundled Nunito Black font in `assets\fonts\`, so they look the same as on the Mac.

## 6. Syncing between the Mac and the PC

Code, scenes, scripts, narration, sound effects and preview PNGs are in git. Renders, videos,
virtual environments and voice models are not (see `.gitignore`).

- **Get the latest changes** (do this before you start working on either machine):
  `git pull`
- **Send your changes** (scene edits, new scripts):
  ```powershell
  git add -A
  git commit -m "Describe what changed"
  git push
  ```
- **Finished videos** (`exports\*.mp4`, `previews\*.mp4`) are git-ignored because they're
  large. Upload the final MP4 to YouTube directly from the PC, or copy it to the Mac with a USB
  drive or a cloud folder (iCloud Drive, Google Drive, OneDrive).

Avoid editing the same file on both machines without pulling in between; if `git pull` reports
a conflict, ask the Cursor agent to resolve it.
