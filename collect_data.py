"""Merge gaze-cueing data into one tidy CSV plus a per-participant summary.

Inputs it understands (give any mix on the command line, or a folder containing them):
  * JSON files downloaded or copied from the task's finish screen (one record per participant)
  * a CSV exported from the Google Sheet's "trials" tab (File > Download > CSV)
  * a CSV exported from the "sessions" tab (the raw_json column is parsed when present)
  * CSV files downloaded from the task's finish screen

Usage:
  python collect_data.py data/raw --study students-oct2026 --out data/students
Writes <out>_trials.csv (one row per trial) and <out>_summary.csv (one row per participant).
Duplicates (same pid and trial) are dropped, so the same record can appear in several inputs safely.
"""
import argparse, csv, json, os, statistics, sys

TRIAL_COLS = ['pid', 'study', 'code', 'block', 'trial', 'type', 'gaze', 'target', 'letter', 'soa', 'congruent',
              'prev_congruent', 'prev_target', 'response', 'correct', 'rt_ms', 'anticipation', 'key_trusted',
              'iti_intended', 'iti_actual', 'direct_intended', 'direct_actual', 'soa_intended', 'soa_actual',
              'dropped_frames', 'tab_hidden', 't_target_onset', 'session_start', 'refresh_hz', 'user_agent', 'source_file']


def norm(v):
    if v is None: return ''
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, str):
        if v == ' ': return 'SPACE'          # the space-bar response, which strip() would erase
        s = v.strip()
        if s.lower() in ('true', 'false', ''): return s.lower()
        return s
    return v


def rows_from_record(rec, src):
    se = rec.get('session', {}) or {}
    env = se.get('env', {}) or {}
    out = []
    for t in rec.get('trials', []):
        r = {c: norm(t.get(c)) for c in TRIAL_COLS}
        r['pid'] = r['pid'] or se.get('pid', '')
        r['study'] = r['study'] or se.get('study', '')
        r['code'] = r['code'] or se.get('code', '')
        r['session_start'] = se.get('start', '')
        r['refresh_hz'] = env.get('refresh_hz', '')
        r['user_agent'] = env.get('ua', '')
        r['source_file'] = src
        out.append(r)
    return out


def load_file(path):
    name = os.path.basename(path)
    rows = []
    if path.lower().endswith('.json'):
        with open(path, encoding='utf-8') as f:
            rec = json.load(f)
        rows += rows_from_record(rec, name)
    elif path.lower().endswith('.jsonl'):                                       # collector.py append-only file or export
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try: rows += rows_from_record(json.loads(line), name)
                except json.JSONDecodeError: pass
    elif path.lower().endswith('.csv'):
        with open(path, encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'raw_json' in row and row['raw_json'].startswith('{'):       # sessions sheet
                    try: rows += rows_from_record(json.loads(row['raw_json']), name)
                    except json.JSONDecodeError: pass
                elif 'rt_ms' in row:                                              # trials sheet or finish-screen CSV
                    r = {c: norm(row.get(c)) for c in TRIAL_COLS}
                    r['source_file'] = name
                    rows.append(r)
    return rows


def to_float(v):
    try: return float(v)
    except (TypeError, ValueError): return None


def summarise(rows):
    by = {}
    for r in rows: by.setdefault(r['pid'], []).append(r)
    out = []
    for pid, rs in by.items():
        exp = [r for r in rs if r['type'] == 'exp']
        catch = [r for r in rs if r['type'] == 'catch']
        ok = [r for r in exp if r['correct'] == 'true' and to_float(r['rt_ms']) is not None and to_float(r['rt_ms']) >= 100]
        rts = [to_float(r['rt_ms']) for r in ok]
        c = [to_float(r['rt_ms']) for r in ok if r['congruent'] == 'true']
        i = [to_float(r['rt_ms']) for r in ok if r['congruent'] == 'false']
        mean = lambda a: round(statistics.mean(a), 1) if a else ''
        out.append({
            'pid': pid, 'study': rs[0]['study'], 'code': rs[0]['code'], 'session_start': rs[0]['session_start'],
            'n_exp': len(exp), 'n_answered': sum(1 for r in exp if r['response'] not in ('', None)),
            'accuracy': round(sum(1 for r in exp if r['correct'] == 'true') / len(exp), 3) if exp else '',
            'anticipations': sum(1 for r in rs if r['anticipation'] == 'true'),
            'catch_false_alarms': sum(1 for r in catch if r['correct'] == 'false'),
            'untrusted_presses': sum(1 for r in rs if r['key_trusted'] == 'false'),
            'rt_mean': mean(rts), 'rt_sd': round(statistics.stdev(rts), 1) if len(rts) > 1 else '',
            'rt_min': min(rts) if rts else '', 'rt_max': max(rts) if rts else '',
            'rt_congruent': mean(c), 'rt_incongruent': mean(i),
            'cueing_effect_ms': round(statistics.mean(i) - statistics.mean(c), 1) if c and i else '',
            'dropped_frames_total': sum(int(to_float(r['dropped_frames']) or 0) for r in rs),
            'tab_hidden_trials': sum(1 for r in rs if r['tab_hidden'] == 'true'),
            'refresh_hz': rs[0]['refresh_hz'],
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='+', help='files or folders')
    ap.add_argument('--study', default='', help='keep only rows with this study label')
    ap.add_argument('--out', default='merged', help='output prefix')
    a = ap.parse_args()

    paths = []
    for p in a.inputs:
        if os.path.isdir(p):
            paths += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.lower().endswith(('.json', '.jsonl', '.csv'))]
        else:
            paths.append(p)
    rows = []
    for p in paths:
        try: rows += load_file(p)
        except Exception as e: print(f'skipped {p}: {e}', file=sys.stderr)
    if a.study: rows = [r for r in rows if r['study'] == a.study]

    seen, uniq = set(), []
    for r in rows:
        k = (r['pid'], r['type'], r['block'], r['trial'])
        if k in seen: continue
        seen.add(k); uniq.append(r)
    uniq.sort(key=lambda r: (r['session_start'], r['pid'], int(to_float(r['block']) or 0), int(to_float(r['trial']) or 0)))

    with open(a.out + '_trials.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=TRIAL_COLS); w.writeheader(); w.writerows(uniq)
    summ = summarise(uniq)
    with open(a.out + '_summary.csv', 'w', newline='', encoding='utf-8') as f:
        if summ:
            w = csv.DictWriter(f, fieldnames=list(summ[0].keys())); w.writeheader(); w.writerows(summ)
    print(f'{len(paths)} files, {len(uniq)} trials, {len(summ)} participants -> {a.out}_trials.csv, {a.out}_summary.csv')
    effects = [s['cueing_effect_ms'] for s in summ if s['cueing_effect_ms'] != '']
    if effects:
        print(f'mean cueing effect across participants: {statistics.mean(effects):.1f} ms (n={len(effects)})')


if __name__ == '__main__':
    main()
