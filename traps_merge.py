"""Merge cognitive-trap survey records (the replica in traps/) into two CSVs.

Inputs: JSON files from the finish screen, the collector's data/incoming folder or its all_records.jsonl,
or export.jsonl from the dashboard. Only records with session.task == "cognitive-traps" are used.

Usage:
  python traps_merge.py data/incoming --study agents-oct2026 --out data/traps
Writes <out>_answers.csv (one row per question) and <out>_summary.csv (one row per participant with
per-trap correctness, traps_correct, flagged_3plus, deferral and attention-check results).
"""
import argparse, csv, json, os, sys

TRAP_ORDER = ['CafeWall', 'Lines', 'Circles', 'Robot', 'Collision', 'Planets']


def records_from(path):
    out = []
    if path.lower().endswith('.json'):
        with open(path, encoding='utf-8') as f: out.append(json.load(f))
    elif path.lower().endswith('.jsonl'):
        with open(path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try: out.append(json.loads(line))
                    except json.JSONDecodeError: pass
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inputs', nargs='+'); ap.add_argument('--study', default=''); ap.add_argument('--out', default='traps')
    a = ap.parse_args()
    paths = []
    for p in a.inputs:
        if os.path.isdir(p): paths += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.lower().endswith(('.json', '.jsonl'))]
        else: paths.append(p)
    recs = []
    for p in paths:
        try: recs += records_from(p)
        except Exception as e: print(f'skipped {p}: {e}', file=sys.stderr)
    recs = [r for r in recs if (r.get('session') or {}).get('task') == 'cognitive-traps']
    if a.study: recs = [r for r in recs if r['session'].get('study') == a.study]
    seen, uniq = set(), []
    for r in recs:
        k = r['session'].get('pid')
        if k in seen: continue
        seen.add(k); uniq.append(r)

    answers, summ = [], []
    for r in uniq:
        se, s = r['session'], r.get('summary', {})
        for row in r.get('trials', []):
            row = dict(row); row['session_start'] = se.get('start', ''); row['agent'] = se.get('agent', ''); answers.append(row)
        per = s.get('per_trap', {})
        summ.append({'pid': se.get('pid'), 'study': se.get('study'), 'condition': se.get('condition'), 'start': se.get('start'),
                     **{t: per.get(t, '') for t in TRAP_ORDER},
                     'traps_correct': s.get('traps_correct'), 'traps_failed': s.get('traps_failed'), 'flagged_3plus': s.get('flagged_3plus'),
                     'deferral': s.get('deferral'), 'imc_pass': s.get('imc_pass'), 'obvious_pass': s.get('obvious_pass'),
                     'memory_pass': s.get('memory_pass'), 'panas_instructed_pass': s.get('panas_instructed_pass'),
                     'total_ms': s.get('total_ms'), 'ua': (se.get('env') or {}).get('ua', '')})
    cols = []
    for row in answers:
        for k in row:
            if k not in cols: cols.append(k)
    with open(a.out + '_answers.csv', 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(answers)
    with open(a.out + '_summary.csv', 'w', newline='', encoding='utf-8') as f:
        if summ: w = csv.DictWriter(f, fieldnames=list(summ[0].keys())); w.writeheader(); w.writerows(summ)
    print(f'{len(uniq)} participants, {len(answers)} answers -> {a.out}_answers.csv, {a.out}_summary.csv')
    if summ:
        n = len(summ)
        for t in TRAP_ORDER:
            vals = [x[t] for x in summ if x[t] != '']
            if vals: print(f'  {t:10s} pass rate {sum(vals) / len(vals):.2f} (n={len(vals)})')
        fl = [x['flagged_3plus'] for x in summ if x['flagged_3plus'] is not None]
        if fl: print(f'  flagged at 3+ failures: {sum(fl)}/{len(fl)}')


if __name__ == '__main__':
    main()
