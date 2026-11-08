#!/bin/zsh
# Synthesize a small library of royalty-free sound effects with ffmpeg into audio/sfx/.
# Everything is generated from noise and sine waves, so there are no licensing questions.
#
#   tools/make_sfx.sh
set -e
out="${0:A:h:h}/audio/sfx"
mkdir -p "$out"
gen() {
  local af=()
  [[ -n "$3" ]] && af=(-af "$3")
  ffmpeg -hide_banner -loglevel error -y -f lavfi -i "$2" "${af[@]}" -ar 48000 -ac 1 "$out/$1.wav"
  echo "  $1"
}

echo "Writing sound effects to $out"
gen pop    "aevalsrc='0.6*sin(2*PI*t*(420+1800*t))*exp(-t*22)':d=0.25"
gen whoosh "anoisesrc=d=1.0:c=pink:a=0.8" "bandpass=f=900:w=1.2,afade=t=in:d=0.4,afade=t=out:st=0.45:d=0.55,volume=2.2"
gen open   "anoisesrc=d=1.2:c=pink:a=0.8" "bandpass=f=1300:w=1.0,afade=t=in:d=0.5,afade=t=out:st=0.6:d=0.6,volume=2.0"
gen close  "anoisesrc=d=1.2:c=pink:a=0.8" "bandpass=f=650:w=1.0,afade=t=in:d=0.5,afade=t=out:st=0.6:d=0.6,areverse,volume=2.0"
gen dig    "anoisesrc=d=0.9:c=brown:a=0.9" "highpass=f=250,lowpass=f=3500,tremolo=f=8:d=0.95,afade=t=out:st=0.5:d=0.4,volume=2.5"
gen warm   "aevalsrc='0.25*sin(2*PI*196*t)+0.18*sin(2*PI*294*t)+0.1*sin(2*PI*392*t)':d=2.2" "afade=t=in:d=0.9,afade=t=out:st=1.2:d=1.0"
gen chime  "aevalsrc='0.35*sin(2*PI*880*t)*exp(-3*t)+0.22*sin(2*PI*1320*t)*exp(-4*t)+0.14*sin(2*PI*1760*t)*exp(-5*t)':d=1.6"
gen steps  "anoisesrc=d=4:c=white:a=0.7" "highpass=f=300,lowpass=f=2200,volume='if(lt(mod(t\,0.5)\,0.07)\,1\,0)':eval=frame,volume=1.5"
gen wind   "anoisesrc=d=70:c=brown:a=0.9" "lowpass=f=500,tremolo=f=0.12:d=0.7,volume=1.4"
