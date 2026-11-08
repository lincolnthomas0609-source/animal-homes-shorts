# Repository sync

This project has two git remotes:

| Remote   | Where                                                                  |
| -------- | ---------------------------------------------------------------------- |
| `origin` | GitHub: https://github.com/lincolnthomas0609-source/animal-homes-shorts.git |
| `cursor` | Cursor-hosted: https://origin.cursor.com/trilogy-cursor-central-account/render-kit.git |

## Big files live in Git LFS

Videos (`*.mp4`, `*.mov`), audio (`*.wav`), images (`*.png`), fonts (`*.ttf`, `*.otf`),
Blender scenes (`*.blend`) and voice models (`*.onnx`, `*.bin`) are stored with
[Git LFS](https://git-lfs.com) (see `.gitattributes`). Run this once per machine before
cloning:

```
git lfs install
```

- macOS: put the `git-lfs` binary on your PATH (e.g. `~/.local/bin`).
- Windows: Git for Windows already includes Git LFS; just run `git lfs install` once.

Not in the repo (regenerate locally): the raw frame folders `renders/*/` (rerun
`tools/render.py`), Blender backups `*.blend1`, and the Python virtualenvs `.venv/` and
`.venv-kokoro/` (see `SETUP_WINDOWS.md`).

## Clone on another machine

```
git lfs install
git clone https://origin.cursor.com/trilogy-cursor-central-account/render-kit.git
```

Cursor-hosted repos need the `origin` CLI signed in (`origin auth login`) so git can authenticate.

## Push updates to both remotes

```
git push cursor main
git push origin main
```
