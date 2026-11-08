"""Synthesize a small library of royalty-free sound effects with ffmpeg into audio/sfx/.
Everything is generated from noise and sine waves, so there are no licensing questions.

    python tools/make_sfx.py [out_dir]     (default audio/sfx)

Cross-platform version of tools/make_sfx.sh.
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shorts_env import ROOT, ffmpeg  # noqa: E402

# name, lavfi source, optional audio filter
SOUNDS = [
    ("pop", "aevalsrc='0.6*sin(2*PI*t*(420+1800*t))*exp(-t*22)':d=0.25", None),
    ("whoosh", "anoisesrc=d=1.0:c=pink:a=0.8",
     "bandpass=f=900:w=1.2,afade=t=in:d=0.4,afade=t=out:st=0.45:d=0.55,volume=2.2"),
    ("open", "anoisesrc=d=1.2:c=pink:a=0.8",
     "bandpass=f=1300:w=1.0,afade=t=in:d=0.5,afade=t=out:st=0.6:d=0.6,volume=2.0"),
    ("close", "anoisesrc=d=1.2:c=pink:a=0.8",
     "bandpass=f=650:w=1.0,afade=t=in:d=0.5,afade=t=out:st=0.6:d=0.6,areverse,volume=2.0"),
    ("dig", "anoisesrc=d=0.9:c=brown:a=0.9",
     "highpass=f=250,lowpass=f=3500,tremolo=f=8:d=0.95,afade=t=out:st=0.5:d=0.4,volume=2.5"),
    ("warm", "aevalsrc='0.25*sin(2*PI*196*t)+0.18*sin(2*PI*294*t)+0.1*sin(2*PI*392*t)':d=2.2",
     "afade=t=in:d=0.9,afade=t=out:st=1.2:d=1.0"),
    ("chime", "aevalsrc='0.35*sin(2*PI*880*t)*exp(-3*t)+0.22*sin(2*PI*1320*t)*exp(-4*t)"
              "+0.14*sin(2*PI*1760*t)*exp(-5*t)':d=1.6", None),
    ("steps", "anoisesrc=d=4:c=white:a=0.7",
     r"highpass=f=300,lowpass=f=2200,volume='if(lt(mod(t\,0.5)\,0.07)\,1\,0)':eval=frame,volume=1.5"),
    ("wind", "anoisesrc=d=70:c=brown:a=0.9", "lowpass=f=500,tremolo=f=0.12:d=0.7,volume=1.4"),
]


def main(argv):
    out = Path(argv[0]) if argv else ROOT / "audio" / "sfx"
    out.mkdir(parents=True, exist_ok=True)
    print(f"Writing sound effects to {out}")
    for name, source, af in SOUNDS:
        subprocess.run([ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", source,
                        *(["-af", af] if af else []), "-ar", "48000", "-ac", "1", str(out / f"{name}.wav")],
                       check=True)
        print(f"  {name}")


if __name__ == "__main__":
    main(sys.argv[1:])
