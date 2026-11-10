# Aurora Express quality review

`tools/qa.py` checked collisions every 0.05 seconds and rendered 23 stills across all 11 shots. The final story returned **0 failures and 0 warnings**.

| Sample times (seconds) | Visual review |
| --- | --- |
| 0.25, 1.68, 3.05, 3.84, 4.36 | The pullback keeps the courier in frame. The title stays inside the active picture and the following portrait shows the face and glowstone. |
| 5.65, 6.96, 8.25, 9.62, 10.95 | The track stays flat, the lightning is separated from the runner and the low angle shows the jump above the falling decking. |
| 12.45, 14.06, 15.55, 16.62, 17.75, 18.85 | The cut preserves the direction of travel. The tower becomes the focal point, then the close-up holds the reaction. |
| 20.00, 21.39, 22.73, 24.29 | The glowstone transfers from the courier's hand to the socket. The camera tilts to follow the signal and particles. |
| 25.75, 28.20, 29.75 | The wide shot contains the broken walkway and the relit tower. The last title reads before the fade. |

The first pass caught the courier slipping out of the opening frame. Reframing the crane fixed it. The visual pass also caught tall rail faces where the renderer turns destructible blocks into cube instances. The rail now has a protected support while the walkway remains destructible.

The encoded MP4 passed `tools/check_media.py` and a full FFmpeg decode. H.264 picture is 1280 × 720, 720 frames at 24 fps, exactly 30.000 seconds. Stereo AAC is 44.1 kHz and also runs 30.000 seconds. FFmpeg measured −19.9 LUFS integrated with a −2.8 dB true peak. The mix measures quieter during the held reaction than during the crossing and the signal cue. Audio was checked by decode, timeline and signal measurements.
