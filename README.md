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

## In-person sessions (students, lab)

One shared link, a unique id per click, all data tagged with a study label and collected centrally.

A page on GitHub Pages cannot write files back into GitHub without a secret key, and a key in a public page would let anyone write to the repo, so the data has to go somewhere else. Three ways, simplest first.

**Option A, no accounts at all: run the collector on your laptop.** In the task folder run
```
python collector.py
```
It prints a link such as `http://192.168.1.23:8731/?study=students-oct2026&repsPerCell=4`. Students on the same Wi-Fi open it (a phone hotspot is the most reliable network; university Wi-Fi sometimes blocks laptop-to-laptop traffic). Every finished run is written to `data/incoming/<pid>.json` and appended to `data/incoming/all_records.jsonl`, a file that is only ever appended to, so a crash cannot corrupt earlier records. Nothing leaves the room.

**Option B, no code: a Google Form.** Create a form with one "paragraph" question, click the three dots > Get pre-filled link, type anything in the box, copy the link and read the `entry.NNNNNNN` part. Share the task link with the form URL and that id:
```
...?study=students-oct2026&formUrl=https://docs.google.com/forms/d/e/FORM_ID/viewform&formEntry=entry.NNNNNNN
```
Each run lands as one response holding the whole record as JSON; link the form to a Sheet (Responses > Sheets icon) and export. No deployment, no authorisation dialogs.

**Option C, Railway, always on, like the outcome-bias platform.** The same `collector.py` runs on Railway. From this folder:
```
railway login
railway init            # new project, name it gaze-cueing-collector
railway up              # deploys; railway.json starts collector.py
railway volume add --mount-path /app/data     # data survives redeploys
railway variables --set EXPORT_KEY=choose-a-secret --set DATA_DIR=/app/data
railway domain          # prints https://xxx.up.railway.app
```
Then share the GitHub Pages link with `dataUrl=https://xxx.up.railway.app/save`, or paste that URL into `DEFAULTS.dataUrl`. Researcher views: `/dashboard?key=...`, `/export.csv?key=...` (one row per trial), `/export.jsonl?key=...` (raw records). The repo can stay public: the data never enters it, only the service holds it.

**Option D, Apps Script to a Google Sheet** (one row per trial, nicer to browse, 5 minutes of setup): create a Sheet, Extensions > Apps Script, paste `apps_script.gs`, Deploy > Web app (execute as me, access: anyone), copy the `/exec` URL and pass it as `dataUrl=` or set `DEFAULTS.dataUrl`.

1. **Pick one of the three** above. Whatever you choose, every trial is also saved in the participant's browser as it happens, and the finish screen has Send again, Copy data and Download JSON.
2. **Share one link** with the study label (for Option A the collector prints it):
   ```
   https://mehdi-lahrach.github.io/gaze-cueing-captcha/?study=students-oct2026&repsPerCell=4
   ```
   Every click gets an id like `students-oct2026-20261022-k3f9q2ab`, so no two students collide and the rows are separate from all test data. `repsPerCell=4` gives 16 trials (about 70 s) instead of 8, which lets you compute the effect from the first 4, 8, 12 and 16 trials.
3. **During the session**: laptops, window maximised, keyboard within reach. At the end each student sees "Your data has been sent". If the network fails they can click "Send again", "Copy data" or "Download JSON". Every trial is also saved in the browser's local storage as it happens, so a closed tab loses nothing.
4. **Afterwards**: in the Sheet, File > Download > CSV for the `trials` tab (and the `sessions` tab, which holds each full record as JSON). Put the files and any downloaded JSON in a folder and run
   ```
   python collect_data.py data/raw --study students-oct2026 --out data/students
   ```
   which writes one clean trial-level CSV and one per-participant summary (accuracy, anticipations, false alarms, untrusted presses, RT mean and spread, congruent and incongruent means, cueing effect). Duplicates are dropped, so overlapping inputs are safe.

Why this layout: JSON is written at the source and kept whole in the `sessions` tab, so a corrupted or half-exported CSV can always be rebuilt from it; the trial rows exist in three places (Sheet, participant's browser, optional download); and the study label keeps the student data apart from every test run.

## Cognitive-trap survey (Affonso 2026 replica)

`traps/index.html` reproduces Affonso's main-study survey page by page from his published Qualtrics file: consent (ours, no reCAPTCHA), the laptop choice (conflict or dominated at random), PANAS with the instructed item, the intro, the six traps in random order with shuffled options and forced answers, the three attention checks, demographics. Page timing and click counts are recorded as in Qualtrics. Served by the same collector and hosted at `/traps/` on GitHub Pages.

```
http://<collector>/traps/?study=agents-oct2026            full survey
http://<collector>/traps/?study=students-oct2026&only=traps   intro + six traps only, about 2 minutes
...&condition=conflict|dominated  ...&showSummary=1  ...&dataUrl=
```
Records carry `task: "cognitive-traps"`; merge them with `python traps_merge.py data/incoming --study <label> --out data/traps`, which gives per-trap correctness, the 3-failure flag, deferral and the attention-check results per participant. His stimuli, trap definitions, survey file and data samples are in `../affonso_materials/`.

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
| `key_trusted` | true for a real keyboard event, false for a key event dispatched by a script inside the page (`event.isTrusted`); the JSON summary counts `untrustedPresses` |
| `iti_intended`, `iti_actual`, `direct_intended`, `direct_actual`, `soa_intended`, `soa_actual` | planned vs measured durations in ms, from requestAnimationFrame timestamps |
| `dropped_frames` | frames longer than 1.5 x the display period during the trial |
| `tab_hidden` | true if the browser tab lost visibility during the trial (browsers then throttle timing to about 1 frame per second); the task pauses before the next trial until the tab is visible again |
| `t_target_onset` | performance.now() timestamp of target onset |

The JSON adds the full config, user agent, viewport, device pixel ratio and estimated refresh rate.

Suggested exclusions for analysis: accuracy below 80%, RTs below 100 ms or above the timeout, trials with `dropped_frames` > 0 or `soa_actual` more than 1 frame off, participants with more than 5% such trials.

## Reaching the laptop collector from the internet (agents in cloud browsers)

A free Cloudflare quick tunnel gives the collector a temporary public address, no account needed:
```
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url http://localhost:8731 --no-autoupdate
```
It prints `https://<random-words>.trycloudflare.com`. Put that in the survey link as `dataUrl=https://<random-words>.trycloudflare.com/save` and every run posts straight into `data/incoming`, wherever the agent runs. The address changes each time the tunnel is restarted, so regenerate the links when you restart it. Keep both the collector and the tunnel windows open while agents work.

### Study 1A preset (27 October 2026)
`?preset=study1a` = the 16-target pilot block with three changes: the target stays until a press or 5 s (`targetTimeoutMs=5000`, catch trials wait 5 s), the gaze-to-target delay is drawn at random between 200 and 400 ms on every trial (`soas=300`, `soaJitterMs=200`; the drawn value is logged as `soa_intended`), and no feedback in the real block (`realFeedback=0`). Agent runs in the built-in browser add `&fullscreen=0`.
