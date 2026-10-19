"""Zero-setup data collector for in-person sessions.

Run this on your laptop, in the task folder:

    python collector.py

It serves the task on your local network and saves every finished run to disk:
    data/incoming/<pid>.json          one file per participant (whole record)
    data/incoming/all_records.jsonl   one line per participant, appended as they arrive (never rewritten)

Students connect to the same Wi-Fi (a phone hotspot is the most reliable) and open the link the script prints, e.g.
    http://192.168.1.23:8731/?study=students-oct2026&askCode=1&repsPerCell=4
The task posts to this script at the end of the run; nothing leaves the room. Afterwards run
    python collect_data.py data/incoming --study students-oct2026 --out data/students
to get the merged CSVs. Press Ctrl+C to stop.
"""
import json, os, socket, sys, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8731
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'data', 'incoming')
os.makedirs(OUT, exist_ok=True)


def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return '127.0.0.1'


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=HERE, **k)

    def do_GET(self):
        # Bare root: add dataUrl=/save so the task posts back here, keeping any params the organiser added.
        u = urlparse(self.path)
        if u.path in ('/', '/index.html'):
            q = parse_qs(u.query, keep_blank_values=True)
            if 'dataUrl' not in q:
                q['dataUrl'] = ['/save']
                self.send_response(302)
                self.send_header('Location', '/index.html?' + urlencode(q, doseq=True))
                self.end_headers()
                return
        return super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != '/save':
            self.send_response(404); self.end_headers(); return
        n = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(n)
        try:
            rec = json.loads(raw.decode('utf-8'))
            pid = str(rec.get('session', {}).get('pid', 'unknown')).replace('/', '_').replace('\\', '_')
        except Exception:
            rec, pid = {'raw': raw.decode('utf-8', 'replace')}, 'unparsed'
        stamp = time.strftime('%Y%m%d-%H%M%S')
        with open(os.path.join(OUT, f'{pid}.json'), 'w', encoding='utf-8') as f:
            json.dump(rec, f, indent=1)
        with open(os.path.join(OUT, 'all_records.jsonl'), 'a', encoding='utf-8') as f:
            f.write(json.dumps({'received_at': stamp, **rec}) + '\n')
        s = rec.get('summary', {}) if isinstance(rec, dict) else {}
        print(f"[{stamp}] saved {pid}: {s.get('nTrials', '?')} trials, accuracy {s.get('accuracy', '?')}", flush=True)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, fmt, *args):   # quiet: only print saves
        pass


if __name__ == '__main__':
    ip = lan_ip()
    srv = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print('Gaze-cueing collector running. Data folder:', OUT)
    print(f'Share this link on the same Wi-Fi:  http://{ip}:{PORT}/?study=students-oct2026&askCode=1&repsPerCell=4')
    print(f'Test it yourself:                   http://localhost:{PORT}/?study=test')
    print('Press Ctrl+C to stop.\n')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nstopped')
