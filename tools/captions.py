"""Build burned-in captions (ASS subtitles) from a narration timing file.

Each narration line is split into short chunks (a few words each), timed in
proportion to their length. Optional labels (species name, season, "Illustrative")
come from the scene's cues file.

    python3 tools/captions.py <timing.json> <out.ass> [--cues renders/<scene>_cues.json]
"""

import argparse
import json
import math
import os
import re

BUNDLED_FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts", "Nunito-Black.ttf")
FONT = "Nunito Black" if os.path.isfile(BUNDLED_FONT) else "Arial Rounded MT Bold"

HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{FONT},84,&H00FFFFFF,&H00FFFFFF,&H00141414,&H64000000,0,0,0,0,100,100,0,0,1,7,3,2,80,80,560,1
Style: Label,{FONT},46,&H00FFFFFF,&H00FFFFFF,&H00141414,&H64000000,0,0,0,0,100,100,1,0,1,4,0,8,60,60,190,1
Style: Note,{FONT},32,&H00E8E8E8,&H00FFFFFF,&H00141414,&H64000000,0,0,0,0,100,100,0,0,1,3,0,7,50,50,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def ts(seconds):
    seconds = max(seconds, 0)
    h = int(seconds // 3600)
    m = int(seconds % 3600 // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def chunks(text, max_words=3, max_chars=22):
    """Split a line into short caption chunks.

    Breaks at punctuation first, then splits each phrase into evenly sized chunks,
    so no chunk straddles a comma and no word is left stranded on its own.
    """
    out = []
    for phrase in re.split(r"(?<=[.,:;?!])\s+", text.strip()):
        words = phrase.split()
        k = math.ceil(len(words) / max_words)
        while True:
            base, extra = divmod(len(words), k)
            sizes = [base + (1 if i < extra else 0) for i in range(k)]
            groups, i = [], 0
            for s in sizes:
                groups.append(words[i:i + s])
                i += s
            if all(len(" ".join(g)) <= max_chars for g in groups) or k >= len(words):
                break
            k += 1
        out += [" ".join(g) for g in groups]
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("timing")
    p.add_argument("out")
    p.add_argument("--cues")
    a = p.parse_args()

    with open(a.timing) as f:
        lines = json.load(f)
    events = []
    for line in lines:
        parts = chunks(line["text"])
        weights = [len(c) + 3 for c in parts]
        t, span = line["start"], line["end"] - line["start"]
        for part, w in zip(parts, weights):
            d = span * w / sum(weights)
            text = part.upper().rstrip(",;:.")
            events.append(f"Dialogue: 0,{ts(t)},{ts(t + d)},Caption,,0,0,0,,{text}")
            t += d

    if a.cues:
        with open(a.cues) as f:
            for label in json.load(f).get("labels", []):
                events.append(f"Dialogue: 1,{ts(label['start'])},{ts(label['end'])},{label.get('style', 'Label')},,0,0,0,,"
                              f"{{\\fad(250,250)}}{label['text']}")

    with open(a.out, "w") as f:
        f.write(HEADER + "\n".join(events) + "\n")
    print(f"Wrote {a.out} ({len(events)} events)")


if __name__ == "__main__":
    main()
