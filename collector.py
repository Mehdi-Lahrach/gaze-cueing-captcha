"""Data collector for the gaze-cueing task. Works in two places with the same file:

LAPTOP (in-person session, no accounts):
    python collector.py
  Serves the task on your local network and saves every finished run under data/incoming/.
  Students on the same Wi-Fi open the printed link.

RAILWAY (always-on, like the outcome-bias platform):
    railway up        (railway.json starts this file; mount a volume at /app/data so data survives redeploys)
  Set EXPORT_KEY in the service variables. The GitHub Pages task then posts to
    https://<your-service>.up.railway.app/save
  via the link parameter  dataUrl=https://<your-service>.up.railway.app/save

Storage, both cases (DATA_DIR, default ./data/incoming):
    <pid>.json          one file per participant, the whole record
    all_records.jsonl   one line per participant, append-only, never rewritten

Researcher endpoints (key = EXPORT_KEY, default "research2025"):
    /dashboard?key=...      list of participants with accuracy, cueing effect, flags
    /export.csv?key=...     one row per trial, all participants (optionally &study=label)
    /export.jsonl?key=...   the raw append-only file
Afterwards: python collect_data.py <export.jsonl or data/incoming> --study <label> --out data/<name>
"""
import csv, io, json, os, socket, sys, time, html
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get('PORT') or (sys.argv[1] if len(sys.argv) > 1 else 8731))
DATA_DIR = os.environ.get('DATA_DIR') or os.path.join(HERE, 'data', 'incoming')
EXPORT_KEY = os.environ.get('EXPORT_KEY', 'research2025')
os.makedirs(DATA_DIR, exist_ok=True)
JSONL = os.path.join(DATA_DIR, 'all_records.jsonl')


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]; s.close(); return ip
    except OSError:
        return '127.0.0.1'


def read_records():
    recs = []
    if os.path.exists(JSONL):
        with open(JSONL, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try: recs.append(json.loads(line))
                    except json.JSONDecodeError: pass
    return recs


def trial_rows(recs, study=None):
    rows = []
    for rec in recs:
        se = rec.get('session', {}) or {}
        if study and se.get('study') != study: continue
        for t in rec.get('trials', []):
            r = {k: ('true' if v is True else 'false' if v is False else '' if v is None else v) for k, v in t.items()}
            r['session_start'] = se.get('start', ''); r['received_at'] = rec.get('received_at', '')
            rows.append(r)
    return rows


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=HERE, **k)

    def _send(self, code, body, ctype='text/plain; charset=utf-8'):
        data = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(data)

    def _authed(self, q):
        return q.get('key', [''])[0] == EXPORT_KEY

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query, keep_blank_values=True)
        if u.path in ('/', '/index.html') and 'dataUrl' not in q and 'formUrl' not in q:
            q['dataUrl'] = ['/save']                       # make the served task post back here
            self.send_response(302); self.send_header('Location', '/index.html?' + urlencode(q, doseq=True)); self.end_headers(); return
        if u.path == '/health':
            return self._send(200, 'ok')
        if u.path in ('/dashboard', '/export.csv', '/export.jsonl'):
            if not self._authed(q): return self._send(403, 'missing or wrong key')
            recs = read_records()
            if u.path == '/export.jsonl':
                raw = open(JSONL, 'rb').read() if os.path.exists(JSONL) else b''
                return self._send(200, raw, 'application/x-ndjson')
            if u.path == '/export.csv':
                rows = trial_rows(recs, q.get('study', [None])[0])
                buf = io.StringIO()
                if rows:
                    cols = list(rows[0].keys())
                    for r in rows:
                        for k in r:
                            if k not in cols: cols.append(k)
                    w = csv.DictWriter(buf, fieldnames=cols, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
                return self._send(200, buf.getvalue(), 'text/csv; charset=utf-8')
            # dashboard
            lines = ['<!doctype html><meta charset="utf-8"><title>Gaze-cueing data</title>',
                     '<style>body{font-family:system-ui;margin:24px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:4px 8px;font-size:14px}th{background:#f3f3f3}</style>',
                     f'<h2>Gaze-cueing collector: {len(recs)} participants</h2>',
                     f'<p><a href="/export.csv?key={html.escape(EXPORT_KEY)}">export.csv</a> · <a href="/export.jsonl?key={html.escape(EXPORT_KEY)}">export.jsonl</a> · data dir {html.escape(DATA_DIR)}</p>',
                     '<table><tr><th>received</th><th>pid</th><th>study</th><th>code</th><th>trials</th><th>accuracy</th><th>effect ms</th><th>untrusted presses</th><th>refresh Hz</th></tr>']
            for rec in reversed(recs):
                se = rec.get('session', {}) or {}; s = rec.get('summary', {}) or {}; env = se.get('env', {}) or {}
                eff = (s.get('rows') or [{}])[0].get('effect')
                is_traps = se.get('task') == 'cognitive-traps'
                lines.append('<tr>' + ''.join(f'<td>{html.escape(str(v if v is not None else ""))}</td>' for v in [
                    rec.get('received_at', ''), se.get('pid', ''), se.get('study', '') + (' (traps)' if is_traps else ''), se.get('code', ''),
                    s.get('nTrials', s.get('traps_answered', '')),
                    s.get('accuracy', f"{s.get('traps_correct', '')}/6 correct" if is_traps else ''),
                    (round(eff, 1) if isinstance(eff, (int, float)) else ('flagged' if s.get('flagged_3plus') else '')),
                    s.get('untrustedPresses', ''), env.get('refresh_hz', '')]) + '</tr>')
            lines.append('</table>')
            return self._send(200, '\n'.join(lines), 'text/html; charset=utf-8')
        return super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != '/save':
            return self._send(404, 'not found')
        n = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(n)
        try:
            rec = json.loads(raw.decode('utf-8'))
            pid = str(rec.get('session', {}).get('pid', 'unknown'))
        except Exception:
            rec, pid = {'raw': raw.decode('utf-8', 'replace')}, 'unparsed'
        pid = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in pid)[:80] or 'unknown'
        stamp = time.strftime('%Y-%m-%dT%H:%M:%S')
        rec = {'received_at': stamp, **rec} if isinstance(rec, dict) else rec
        with open(os.path.join(DATA_DIR, f'{pid}.json'), 'w', encoding='utf-8') as f:
            json.dump(rec, f, indent=1)
        with open(JSONL, 'a', encoding='utf-8') as f:
            f.write(json.dumps(rec) + '\n')
        s = rec.get('summary', {}) if isinstance(rec, dict) else {}
        print(f"[{stamp}] saved {pid}: {s.get('nTrials', '?')} trials, accuracy {s.get('accuracy', '?')}", flush=True)
        return self._send(200, '{"ok":true}', 'application/json')

    def log_message(self, fmt, *args):
        pass


if __name__ == '__main__':
    srv = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    on_railway = bool(os.environ.get('RAILWAY_ENVIRONMENT'))
    print(f'Gaze-cueing collector on port {PORT}. Data dir: {DATA_DIR}', flush=True)
    if not on_railway:
        ip = lan_ip()
        print(f'Share on the same Wi-Fi:  http://{ip}:{PORT}/?study=students-oct2026&repsPerCell=4')
        print(f'Dashboard:               http://localhost:{PORT}/dashboard?key={EXPORT_KEY}')
        print('Press Ctrl+C to stop.\n', flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nstopped')
