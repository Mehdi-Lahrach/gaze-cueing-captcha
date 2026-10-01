# Gaze cueing task

Single-file, dependency-free browser task (`index.html`). Schematic circle face looks at the participant, shifts its gaze left or right, then a target appears left or right. Response time and accuracy are recorded per trial with frame-level timing checks.

Open `index.html` in Chrome, Edge or Firefox. No server needed, but hosting it (GitHub Pages, lab server, Pavlovia-style static host) is required for Prolific.

## Trial

1. Blank, `itiMs` + random jitter up to `itiJitterMs`.
2. Face with direct gaze for `directGazeMs`.
3. Pupils jump left or right (`gazeShift`: abrupt or animated).
4. After the SOA (random from `soas`) the target appears, or nothing on catch trials.
5. Response until key press or `targetTimeoutMs`. Catch trials wait `catchHoldMs`.

## Presets

| Preset | Use | Trials | Approx. time |
|---|---|---|---|
| `captcha` (default) | the agreed CAPTCHA block (1 Oct 2026): detection with the space bar, 1 s direct gaze with 800 to 1,200 ms jitter, 250 ms SOA | 8 trials in 2 balanced blocks of 4 (gaze L/R x compatible/incompatible once per block) + 2 catch trials, 2 practice | about 45 s |
| `captcha` with `repsPerCell=4` | pilot version to test how many trials are needed | 16 trials in 4 balanced blocks + 2 catch | about 1.2 min |
| `full` | validation study, localization | 2 SOAs x 2 gaze x 2 side x 16 reps = 128 + 13 catch, 4 blocks, 12 practice | 9 to 10 min |
| `short` | 1-SOA localization block | 1 SOA (300 ms), 675 ms direct gaze, 32 trials, no catch, 4 practice | about 1.5 min |

The agreed CAPTCHA:

```
index.html?preset=captcha
```

Videos of the four configurations are produced by `python make_videos.py` into `videos/` (needs Pillow and ffmpeg).

## Config switches

Edit `DEFAULTS` at the top of the script, or override any key from the URL:

```
index.html?preset=short&responseTask=discrimination&soas=300,700&repsPerCell=12
```

| Key | Default | Meaning |
|---|---|---|
| `responseTask` | `localization` | `detection`: press `keyDetect` when the target appears, any side (needs catch trials). `localization`: F = left target, J = right target. `discrimination`: target is a letter, F = first letter, J = second |
| `keyDetect` | space | detection key |
| `keyLeft`, `keyRight` | `f`, `j` | response keys for localization and discrimination |
| `discrimTargets` | `T,L` | letters in discrimination mode |
| `discrimMapping` | `TL` | `TL`: T on F, L on J. `LT` reverses (counterbalance across participants) |
| `directGazeMs` | 1000 | direct-gaze pre-cue duration |
| `directGazeJitterMs` | 0 | total uniform jitter around `directGazeMs`; 400 gives 800 to 1,200 ms, so the target moment cannot be predicted |
| `soas` | `300,1000` | gaze shift to target onset, randomised across trials |
| `gazeShift` | `abrupt` | `abrupt` (one frame) or `animated` (glide over `gazeAnimMs`, default 120) |
| `targetTimeoutMs` | 1500 | response window |
| `catchHoldMs` | 1500 | wait on catch trials |
| `itiMs`, `itiJitterMs` | 700, 300 | blank between trials |
| `repsPerCell` | 16 | trials per gaze x side x SOA cell at validity .5 |
| `cueValidity` | 0.5 | proportion congruent. 0.2 gives a counter-predictive block |
| `catchProportion` | 0.10 | catch trials relative to experimental trials |
| `catchCount` | 0 | absolute number of catch trials, overrides the proportion when above 0 |
| `blockDesign` | `random` | `random`: shuffle all trials and split into `blocks`. `balanced`: blocks of 4 with each gaze x compatibility configuration once, shuffled within block; catch trials are spread over blocks and never first |
| `blocks` | 4 | number of blocks in the random design |
| `blockBreaks` | true | show a break screen between blocks |
| `practiceTrials` | 12 | practice trials with feedback (`practiceFeedback`) |
| `faceDiameter`, `eyeDiameter`, `eyeOffsetX`, `eyeOffsetY`, `pupilDiameter`, `pupilShift`, `targetEcc`, `targetSize` | 260, 44, 50, -35, 20, 14, 350, 40 | geometry in px, about 40 px per degree at 60 cm on a laptop |
| `fullscreen` | true | request fullscreen at start |
| `showSummary` | false | show the participant their cueing effect at the end |
| `dataUrl` | empty | if set, POST the JSON record here at the end |
| `completionUrl` | empty | Finish button link, for Prolific completion |
| `pid` | random | participant id; `?PROLIFIC_PID=` is also read |

Prolific example link:

```
https://your.host/gaze-cueing-task/index.html?PROLIFIC_PID={{%PROLIFIC_PID%}}&completionUrl=https://app.prolific.com/submissions/complete?cc=XXXX
```

## Static frames for the LLM arm

```
index.html?frame=1&gaze=center
index.html?frame=1&gaze=left&target=none
index.html?frame=1&gaze=left&target=right
index.html?frame=1&gaze=right&target=right&responseTask=discrimination&letter=T
```

Add `&png=1` to download the frame as PNG at the current window size. The same SVG code draws the human and LLM stimuli, so the images are identical to what participants see.

## Data

At the end the participant gets Download CSV / Download JSON buttons. The record is also kept in `localStorage` under `gaze_cueing_<pid>` and exposed as `window.__gazeCueingRecord`. If `dataUrl` is set the JSON is POSTed.

CSV columns, one row per trial:

| Column | Meaning |
|---|---|
| `pid`, `block`, `trial`, `type` | `type` is `practice`, `exp` or `catch` |
| `gaze`, `target`, `letter`, `soa`, `congruent`, `prev_congruent`, `prev_target` | design variables; `prev_*` refer to the previous experimental or catch trial (a repeated target location speeds the next response) |
| `response`, `correct`, `rt_ms`, `anticipation` | key, correctness, RT from target onset; `anticipation` = pressed before target onset |
| `iti_intended`, `iti_actual`, `direct_intended`, `direct_actual`, `soa_intended`, `soa_actual` | planned vs measured durations in ms, from requestAnimationFrame timestamps |
| `dropped_frames` | frames longer than 1.5 x the display period during the trial |
| `tab_hidden` | true if the browser tab lost visibility during the trial (browsers then throttle timing to about 1 frame per second); the task pauses before the next trial until the tab is visible again |
| `t_target_onset` | performance.now() timestamp of target onset |

The JSON adds the full config, user agent, viewport, device pixel ratio and estimated refresh rate.

Suggested exclusions for analysis: accuracy below 80%, RTs below 100 ms or above the timeout, trials with `dropped_frames` > 0 or `soa_actual` more than 1 frame off, participants with more than 5% such trials.
