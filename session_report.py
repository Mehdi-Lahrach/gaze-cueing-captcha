"""One row per student: gaze-task metrics and trap results joined on the participant id.

Usage:
  python session_report.py data/incoming --study students-oct2026 --out data/students_session
Writes <out>.csv and prints group means. Uses collect_data.py and traps_merge.py logic, so run from the task folder.
"""
import argparse, csv, json, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collect_data, traps_merge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='+'); ap.add_argument('--study', default=''); ap.add_argument('--out', default='session')
    a = ap.parse_args()
    paths = []
    for p in a.inputs:
        if os.path.isdir(p): paths += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.lower().endswith(('.json', '.jsonl'))]
        else: paths.append(p)

    gaze_rows, trap_recs = [], []
    for p in paths:
        for rec in traps_merge.records_from(p):
            se = rec.get('session') or {}
            if a.study and se.get('study') != a.study: continue
            if se.get('task') == 'cognitive-traps': trap_recs.append(traps_merge.score(rec))
            else: gaze_rows += collect_data.rows_from_record(rec, os.path.basename(p))
    seen, uniq = set(), []
    for r in gaze_rows:
        k = (r['pid'], r['type'], r['block'], r['trial'])
        if k not in seen: seen.add(k); uniq.append(r)
    gaze = {s['pid']: s for s in collect_data.summarise(uniq)}
    traps = {}
    for rec in trap_recs:
        pid = rec['session'].get('pid'); s = rec.get('summary', {})
        if pid in traps: continue
        row = {'traps_correct': s.get('traps_correct'), 'traps_flagged_3plus': s.get('flagged_3plus')}
        for t in traps_merge.TRAP_ORDER: row['trap_' + t] = s.get('per_trap', {}).get(t, '')
        traps[pid] = row

    pids = sorted(set(gaze) | set(traps))
    cols = ['pid', 'study', 'code', 'gaze_n_exp', 'gaze_accuracy', 'gaze_anticipations', 'gaze_false_alarms', 'gaze_untrusted',
            'gaze_rt_mean', 'gaze_rt_sd', 'gaze_rt_congruent', 'gaze_rt_incongruent', 'gaze_effect_ms',
            'traps_correct', 'traps_flagged_3plus'] + ['trap_' + t for t in traps_merge.TRAP_ORDER]
    out = []
    for pid in pids:
        g = gaze.get(pid, {}); t = traps.get(pid, {})
        out.append({'pid': pid, 'study': g.get('study', a.study), 'code': g.get('code', ''), 'gaze_n_exp': g.get('n_exp', ''),
                    'gaze_accuracy': g.get('accuracy', ''), 'gaze_anticipations': g.get('anticipations', ''),
                    'gaze_false_alarms': g.get('catch_false_alarms', ''), 'gaze_untrusted': g.get('untrusted_presses', ''),
                    'gaze_rt_mean': g.get('rt_mean', ''), 'gaze_rt_sd': g.get('rt_sd', ''), 'gaze_rt_congruent': g.get('rt_congruent', ''),
                    'gaze_rt_incongruent': g.get('rt_incongruent', ''), 'gaze_effect_ms': g.get('cueing_effect_ms', ''),
                    **{c: t.get(c, '') for c in cols if c.startswith('trap')}})
    with open(a.out + '.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(out)
    eff = [r['gaze_effect_ms'] for r in out if r['gaze_effect_ms'] != '']
    tc = [r['traps_correct'] for r in out if r['traps_correct'] not in ('', None)]
    print(f'{len(out)} participants -> {a.out}.csv  (gaze data for {len(gaze)}, traps for {len(traps)})')
    if eff: print(f'  mean gaze-cueing effect: {statistics.mean(eff):.1f} ms  (sd across people {statistics.stdev(eff):.1f} ms, n={len(eff)})' if len(eff) > 1 else f'  gaze effect: {eff[0]} ms')
    if tc: print(f'  mean traps correct: {statistics.mean(tc):.2f} of 6; flagged: {sum(1 for r in out if r["traps_flagged_3plus"] == 1)}')


if __name__ == '__main__':
    main()
