# Third-party assets

## Fonts

| File | Font | License | Source |
| --- | --- | --- | --- |
| `fonts/Nunito-Black.ttf` | Nunito Black (v3.601, static), font family name `Nunito Black` | SIL Open Font License 1.1, full text in `fonts/OFL.txt` | <https://github.com/google/fonts/blob/57661967c8617c151bfbb804945cf64b21d5dad6/ofl/nunito/Nunito-Black.ttf> |

Copyright 2014 The Nunito Project Authors (<https://github.com/googlefonts/nunito>).
The file is unmodified. It comes from the last `google/fonts` commit that shipped static
Nunito weights (the current `ofl/nunito/` folder has only a variable font, which
libass does not render at the Black weight).

Nunito Black replaces macOS's Arial Rounded MT Bold for burned-in captions, so captions
look the same on macOS and Windows. `tools/captions.py` and `tools/assemble.py` use it when
`assets/fonts/` exists.

The OFL allows using, bundling and redistributing the font, including in videos. It can't
be sold on its own.
