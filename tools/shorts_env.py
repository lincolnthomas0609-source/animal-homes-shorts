"""Shared paths for the cross-platform (macOS and Windows) Python tools in this folder.

    from shorts_env import ROOT, blender, ffmpeg, ffprobe, blender_env

Blender: the BLENDER environment variable, then the usual install folders, then PATH.
ffmpeg/ffprobe: the FFMPEG/FFPROBE environment variables, then tools/bin/ in this project,
then PATH, ~/.local/bin, C:\\ffmpeg\\bin and other common Windows folders.

Run it directly to see what was found:  python tools/shorts_env.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WINDOWS = os.name == "nt"
EXE = ".exe" if WINDOWS else ""

# Console output on Windows is often cp1252; don't crash on Blender's non-ASCII log lines.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(errors="replace")


class ToolNotFound(SystemExit):
    pass


def _program_files():
    dirs = [os.environ.get(v) for v in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)")]
    dirs.append(r"C:\Program Files")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        dirs.append(os.path.join(local, "Programs"))
    seen, out = set(), []
    for d in dirs:
        if d and d.lower() not in seen:
            seen.add(d.lower())
            out.append(Path(d))
    return out


def _blender_candidates():
    if WINDOWS:
        for base in _program_files():
            foundation = base / "Blender Foundation"
            yield foundation / "Blender 5.2" / "blender.exe"
            if foundation.is_dir():
                # Newest version first: "Blender 5.2", "Blender 4.5", ...
                for d in sorted(foundation.glob("Blender*"), reverse=True):
                    yield d / "blender.exe"
    elif sys.platform == "darwin":
        yield Path.home() / "Applications/Blender.app/Contents/MacOS/Blender"
        yield Path("/Applications/Blender.app/Contents/MacOS/Blender")
    found = shutil.which("blender")
    if found:
        yield Path(found)


def _is_exe(p):
    return p.is_file() and (WINDOWS or os.access(str(p), os.X_OK))


def find_blender():
    env = os.environ.get("BLENDER")
    if env:
        if _is_exe(Path(env)):
            return str(Path(env))
        raise ToolNotFound(f"BLENDER is set to {env!r}, but that file doesn't exist")
    for candidate in _blender_candidates():
        if _is_exe(candidate):
            return str(candidate)
    if WINDOWS:
        hint = r"Install Blender 5.2 to C:\Program Files\Blender Foundation\ or set BLENDER to blender.exe"
    else:
        hint = "Install it to ~/Applications/Blender.app or set BLENDER"
    raise ToolNotFound(f"Blender not found. {hint}")


def _ffmpeg_dirs():
    yield ROOT / "tools" / "bin"
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if d:
            yield Path(d)
    yield Path.home() / ".local" / "bin"
    if WINDOWS:
        yield Path(r"C:\ffmpeg\bin")
        for base in _program_files():
            yield base / "ffmpeg" / "bin"
        local = os.environ.get("LOCALAPPDATA")
        if local:
            yield Path(local) / "Microsoft" / "WinGet" / "Links"
        yield Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "chocolatey" / "bin"
        yield Path.home() / "scoop" / "shims"
    else:
        yield Path("/opt/homebrew/bin")
        yield Path("/usr/local/bin")


def find_ffmpeg_tool(name):
    """Path to ffmpeg or ffprobe."""
    env = os.environ.get(name.upper())
    if env:
        if _is_exe(Path(env)):
            return str(Path(env))
        raise ToolNotFound(f"{name.upper()} is set to {env!r}, but that file doesn't exist")
    for d in _ffmpeg_dirs():
        candidate = d / (name + EXE)
        if _is_exe(candidate):
            return str(candidate)
    if WINDOWS:
        hint = r"Unzip an ffmpeg build to C:\ffmpeg (so C:\ffmpeg\bin\ffmpeg.exe exists) or copy ffmpeg.exe and ffprobe.exe into tools\bin\ "
    else:
        hint = "Put it on PATH or in ~/.local/bin"
    raise ToolNotFound(f"{name} not found. {hint}")


_cache = {}


def _cached(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


def blender():
    return _cached("blender", find_blender)


def ffmpeg():
    return _cached("ffmpeg", lambda: find_ffmpeg_tool("ffmpeg"))


def ffprobe():
    return _cached("ffprobe", lambda: find_ffmpeg_tool("ffprobe"))


def blender_env():
    """Environment for Blender subprocesses: SHORTS_ROOT points at this project."""
    env = dict(os.environ)
    env["SHORTS_ROOT"] = str(ROOT)
    os.environ["SHORTS_ROOT"] = str(ROOT)
    return env


def filter_path(path):
    """A file path quoted for use inside an ffmpeg filter option, e.g. fontfile=... or subtitles=...

    Forward slashes everywhere; the drive-letter colon (C:) is escaped.
    """
    p = Path(path).as_posix().replace("'", r"'\''").replace(":", r"\:")
    return f"'{p}'"


BUNDLED_FONT = ROOT / "assets" / "fonts" / "Nunito-Black.ttf"


def run_blender(args, keep):
    """Run Blender with args, printing only output lines for which keep(line) is true.

    Like the zsh tools, Blender's exit status is not checked; callers check the frames instead.
    """
    cmd = [blender(), *args]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=blender_env(),
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    try:
        for line in proc.stdout:
            line = line.rstrip("\r\n")
            if keep(line):
                print(line, flush=True)
        return proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        proc.wait()
        raise


def main():
    print(f"SHORTS_ROOT = {ROOT}")
    for label, fn in (("Blender", blender), ("ffmpeg", ffmpeg), ("ffprobe", ffprobe)):
        try:
            print(f"{label:8s}= {fn()}")
        except ToolNotFound as e:
            print(f"{label:8s}: {e}")
    try:
        out = subprocess.run([blender(), "--version"], capture_output=True, text=True, timeout=60).stdout
        print("Blender version:", out.splitlines()[0] if out else "?")
    except (ToolNotFound, OSError, subprocess.TimeoutExpired):
        pass


if __name__ == "__main__":
    main()
