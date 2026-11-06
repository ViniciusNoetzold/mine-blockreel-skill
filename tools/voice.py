#!/usr/bin/env python3
"""Character voices from the TTS voices already on the machine (no download, nothing sent anywhere).

  python tools/voice.py fetch                    # neural offline voices (Piper, CC0 datasets) -> work/voices/ (~63 MB each)
  python tools/voice.py list
  python tools/voice.py say "O farol cai esta noite." --voice piper:faber --preset villain --rate=-35% --out vigia.wav
  (a negative rate must be written with "=", e.g. --rate=-20%; measure each line and fit it to its shot / lip-sync window)
  python tools/voice.py say "O farol cai <break time='150ms'/> esta <emphasis>noite</emphasis>." --voice daniel --preset villain --out vigia.wav
  python tools/voice.py say "Não enquanto eu respirar!" --voice maria --preset hero --out brasa.wav

Windows: uses the WinRT/OneCore voices (better than the old SAPI "Desktop" ones), driven by SSML, so a line can carry pauses
(<break time='200ms'/>), emphasis (<emphasis level='strong'>) and per-word prosody. Then a preset shapes the character with
ffmpeg (pitch, chorus, room, EQ) and trims the silence the TTS engine adds, so the line starts exactly at its cue.
Other systems: not supported yet (record the lines, or add a backend). Install more voices in Windows Settings > Time & language >
Speech (e.g. pt-BR "Daniel" and "Maria"); this tool lists what is installed.

Presets (pitch in semitones, rate, ffmpeg chain):
  hero     natural, slightly brighter, short room
  villain  -4 st, slower, chorus + long echo + low-pass (big, inhuman)
  monster  -7 st, growl (tremolo), long echo
  child    +4 st, faster
  narrator -1 st, slower, warm EQ, small room
  radio    band-limited, a little distortion
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

PRESETS = {  # pitch (semitones), ssml rate, ffmpeg filter after the pitch shift
    "hero": (0, "+4%", "highpass=f=110,equalizer=f=3200:t=q:w=1:g=3,aecho=0.8:0.25:22:0.18"),
    "villain": (-4, "-12%", "chorus=0.6:0.8:40|55:0.35|0.3:0.25|0.4:2|1.6,lowpass=f=3800,aecho=0.8:0.5:80|150:0.3|0.18"),
    "monster": (-7, "-15%", "tremolo=f=28:d=0.35,lowpass=f=3000,aecho=0.8:0.55:90|180:0.35|0.2"),
    "child": (4, "+10%", "highpass=f=180"),
    "narrator": (-1, "-6%", "equalizer=f=180:t=q:w=1:g=2,aecho=0.8:0.2:18:0.12"),
    "radio": (0, "+0%", "highpass=f=400,lowpass=f=3200,acrusher=bits=10:mix=0.3"),
    "none": (0, "+0%", "anull"),
}
TRIM = "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse"

PS_SYNTH = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$m = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, $t) { $task = $m.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(-1) | Out-Null; $task.Result }
[Windows.Media.SpeechSynthesis.SpeechSynthesizer,Windows.Media.SpeechSynthesis,ContentType=WindowsRuntime] | Out-Null
[Windows.Storage.Streams.DataReader,Windows.Storage.Streams,ContentType=WindowsRuntime] | Out-Null
$s = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$v = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | ? { $_.DisplayName -like '*VOICE*' } | Select-Object -First 1
if (-not $v) { Write-Error 'voice not installed: VOICE'; exit 3 }
$s.Voice = $v
$ssml = [IO.File]::ReadAllText('SSMLFILE', [Text.Encoding]::UTF8)
$st = Await ($s.SynthesizeSsmlToStreamAsync($ssml)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
$r = New-Object Windows.Storage.Streams.DataReader($st.GetInputStreamAt(0))
Await ($r.LoadAsync([uint32]$st.Size)) ([uint32]) | Out-Null
$b = New-Object byte[] $st.Size; $r.ReadBytes($b); [IO.File]::WriteAllBytes('OUTFILE', $b)
"""

PS_LIST = r"""
[Windows.Media.SpeechSynthesis.SpeechSynthesizer,Windows.Media.SpeechSynthesis,ContentType=WindowsRuntime] | Out-Null
[Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices | % { $_.DisplayName + ' | ' + $_.Language + ' | ' + $_.Gender }
"""


ROOT = Path(__file__).resolve().parents[1]
VOICES = ROOT / "work" / "voices"
PIPER = {"faber": "pt_BR-faber-medium", "cadu": "pt_BR-cadu-medium", "jeff": "pt_BR-jeff-medium", "edresson": "pt_BR-edresson-low"}
HF = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/{v}/{q}/{n}.{ext}"


def fetch(names=("faber", "cadu")):
    """Download Piper pt-BR voices (offline neural TTS; the datasets are CC0 per each MODEL_CARD) into work/voices/."""
    import urllib.request
    VOICES.mkdir(parents=True, exist_ok=True)
    for v in names:
        n = PIPER[v]; q = n.rsplit("-", 1)[1]
        for ext in ("onnx", "onnx.json"):
            dst = VOICES / f"{n}.{ext}"
            if not dst.exists():
                urllib.request.urlretrieve(HF.format(v=v, q=q, n=n, ext=ext), dst)
        print("voice ready:", VOICES / f"{n}.onnx")


def piper_raw(text, voice, rate, raw):
    import re
    n = PIPER[voice.split(":", 1)[1]]; model = VOICES / f"{n}.onnx"
    if not model.exists():
        raise SystemExit(f"missing {model}: run  python tools/voice.py fetch")
    plain = re.sub(r"<[^>]+>", " ", text).strip()                 # Piper reads plain text (SSML tags are dropped)
    pct = float((rate or "+0%").strip("%")); length = max(0.5, 1 - pct / 100)
    subprocess.run([sys.executable, "-m", "piper", "-m", str(model), "-f", str(raw), "--length-scale", f"{length:.3f}"],
                   input=plain, text=True, check=True, capture_output=True)


def ps(script):
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr.strip() or "TTS failed")
    return r.stdout


def lang_of(voice):
    for line in ps(PS_LIST).splitlines():
        name, lang, _ = (x.strip() for x in line.split("|"))
        if voice.lower() in name.lower():
            return lang
    raise SystemExit(f"voice not installed: {voice} (python tools/voice.py list)")


def say(text, voice, preset, out, pitch_extra=0.0, rate=None, volume=1.0):
    if sys.platform != "win32":
        if not voice.startswith("piper:"):
            raise SystemExit("system voices need Windows; use --voice piper:faber (python tools/voice.py fetch) or record the line")
    semis, ssml_rate, chain = PRESETS[preset]
    semis += pitch_extra
    tmp = Path(tempfile.mkdtemp(prefix="br_voice_")); raw = tmp / "raw.wav"
    if voice.startswith("piper:"):
        piper_raw(text, voice, rate or ssml_rate, raw)
        return finish(raw, semis, chain, volume, out, voice, preset)
    lang = lang_of(voice)
    ssml = (f"<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{lang}'>"
            f"<prosody rate='{rate or ssml_rate}'>{text}</prosody></speak>")
    (tmp / "line.ssml").write_text(ssml, encoding="utf-8")
    ps(PS_SYNTH.replace("VOICE", voice).replace("SSMLFILE", str(tmp / "line.ssml")).replace("OUTFILE", str(raw)))
    return finish(raw, semis, chain, volume, out, voice, preset)


def finish(raw, semis, chain, volume, out, voice, preset):
    factor = 2 ** (semis / 12)
    pitch = f"aresample=44100,asetrate=44100*{factor:.5f},aresample=44100,atempo={1 / factor:.5f}," if semis else "aresample=44100,"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-af", f"{TRIM},{pitch}{chain},volume={volume}",
                    "-ar", "44100", "-ac", "2", str(out)], check=True)
    d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
    print(f"wrote {out} ({float(d):.2f} s, {voice}, {preset})")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list"); sub.add_parser("fetch")
    s = sub.add_parser("say"); s.add_argument("text"); s.add_argument("--voice", required=True); s.add_argument("--out", required=True)
    s.add_argument("--preset", choices=sorted(PRESETS), default="none"); s.add_argument("--pitch", type=float, default=0.0)
    s.add_argument("--rate"); s.add_argument("--volume", type=float, default=1.0)
    a = ap.parse_args(argv)
    if a.cmd == "fetch":
        fetch(); return 0
    if a.cmd == "list":
        print(ps(PS_LIST).strip()); return 0
    say(a.text, a.voice, a.preset, a.out, a.pitch, a.rate, a.volume); return 0


if __name__ == "__main__":
    sys.exit(main())
