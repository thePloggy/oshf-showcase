#!/usr/bin/env python3
"""Vitrine #OpenSourceHiggsfield : sert public/ et l'API de vote.

Règle de vote : chaque visiteur, identifié par son adresse IP, dispose de 10 points à répartir librement
entre les projets, et peut les retirer pour les redonner ailleurs. L'IP n'est jamais stockée en clair :
seule une empreinte HMAC-SHA256 avec un sel secret local (data/sel.bin) est gardée.

API :
  GET  /api/state            -> {"totals": {id: points}, "mine": {id: points}, "left": n, "budget": 10}
  POST /api/vote {"id", "delta": +1|-1}  -> même réponse
"""
import hashlib, hmac, ipaddress, json, os, secrets, sqlite3, threading, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ICI = os.path.dirname(os.path.abspath(__file__))
PUBLIC = os.path.join(ICI, 'public')
DATA = os.path.join(ICI, 'data')
BUDGET = 10
HOTE, PORT = os.environ.get('OSHF_HOST', '127.0.0.1'), int(os.environ.get('OSHF_PORT', '8790'))
# proxys de confiance dont on lit X-Forwarded-For (tailscale serve/funnel parle depuis 127.0.0.1)
PROXYS = {'127.0.0.1', '::1'}
# origines autorisées à appeler l'API depuis un navigateur (la page publique sur GitHub Pages)
ORIGINES = {o for o in os.environ.get('OSHF_ORIGINS', 'https://theploggy.github.io').split(',') if o}

sel_f = os.path.join(DATA, 'sel.bin')
if not os.path.exists(sel_f):
    with open(sel_f, 'wb') as f:
        f.write(secrets.token_bytes(32))
    os.chmod(sel_f, 0o600)
SEL = open(sel_f, 'rb').read()

IDS = {p['id'] for p in json.load(open(os.path.join(PUBLIC, 'projects.json')))['projects']}

db = sqlite3.connect(os.path.join(DATA, 'votes.db'), check_same_thread=False, isolation_level=None)
db.execute('PRAGMA journal_mode=WAL')
db.execute('CREATE TABLE IF NOT EXISTS alloc (voter TEXT NOT NULL, project TEXT NOT NULL, points INTEGER NOT NULL, '
           'updated REAL NOT NULL, PRIMARY KEY (voter, project))')
verrou = threading.Lock()

# limite de débit simple : 30 votes par 10 s par votant
fenetre = {}


def trop_vite(v):
    t = time.time()
    h = [x for x in fenetre.get(v, []) if t - x < 10]
    h.append(t)
    fenetre[v] = h
    return len(h) > 30


def etat(voter):
    totals = {p: n for p, n in db.execute('SELECT project, SUM(points) FROM alloc GROUP BY project HAVING SUM(points) > 0')}
    mine = {p: n for p, n in db.execute('SELECT project, points FROM alloc WHERE voter = ? AND points > 0', (voter,))}
    voters = db.execute('SELECT COUNT(DISTINCT voter) FROM alloc WHERE points > 0').fetchone()[0]
    return {'totals': totals, 'mine': mine, 'left': BUDGET - sum(mine.values()), 'budget': BUDGET, 'voters': voters}


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=PUBLIC, **k)

    def log_message(self, fmt, *args):  # pas d'IP dans les journaux
        pass

    def end_headers(self):
        o = self.headers.get('Origin')
        if self.path.startswith('/api/') and o in ORIGINES:
            self.send_header('Access-Control-Allow-Origin', o)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Access-Control-Max-Age', '600')
            # machines du tailnet : forge y a une adresse privée ; Chrome demande alors l'accès au réseau local
            if self.headers.get('Access-Control-Request-Private-Network'):
                self.send_header('Access-Control-Allow-Private-Network', 'true')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
                                                    "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        if self.path.startswith('/shots/'):
            self.send_header('Cache-Control', 'public, max-age=86400')
        super().end_headers()

    def votant(self):
        ip = self.client_address[0]
        if ip in PROXYS:
            xff = self.headers.get('X-Forwarded-For', '')
            if xff:
                ip = xff.split(',')[0].strip()
        try:
            a = ipaddress.ip_address(ip)
            if a.version == 6:  # un /64 = un foyer
                ip = str(ipaddress.ip_network(f'{a}/64', strict=False).network_address)
        except ValueError:
            pass
        return hmac.new(SEL, ip.encode(), hashlib.sha256).hexdigest()

    def json(self, code, obj):
        b = json.dumps(obj, separators=(',', ':')).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path.split('?')[0] == '/api/state':
            with verrou:
                return self.json(200, etat(self.votant()))
        if self.path.startswith('/api/'):
            return self.json(404, {'error': 'not found'})
        return super().do_GET()

    def do_OPTIONS(self):
        ok = self.path.startswith('/api/') and self.headers.get('Origin') in ORIGINES
        self.send_response(204 if ok else 403)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_POST(self):
        if self.path != '/api/vote':
            return self.json(404, {'error': 'not found'})
        try:
            n = int(self.headers.get('Content-Length', '0'))
            if n > 200:
                raise ValueError
            req = json.loads(self.rfile.read(n))
            pid, delta = req['id'], int(req['delta'])
            if pid not in IDS or delta not in (1, -1):
                raise ValueError
        except Exception:
            return self.json(400, {'error': 'bad request'})
        v = self.votant()
        if trop_vite(v):
            return self.json(429, {'error': 'slow down'})
        with verrou:
            mine = dict(db.execute('SELECT project, points FROM alloc WHERE voter = ?', (v,)).fetchall())
            cur = mine.get(pid, 0)
            nouveau = cur + delta
            if nouveau < 0 or (delta > 0 and sum(mine.values()) >= BUDGET):
                return self.json(409, dict(etat(v), error='no points left' if delta > 0 else 'nothing to remove'))
            db.execute('INSERT INTO alloc (voter, project, points, updated) VALUES (?, ?, ?, ?) '
                       'ON CONFLICT(voter, project) DO UPDATE SET points = excluded.points, updated = excluded.updated',
                       (v, pid, nouveau, time.time()))
            return self.json(200, etat(v))


if __name__ == '__main__':
    print(f'oshf-showcase sur http://{HOTE}:{PORT}', flush=True)
    ThreadingHTTPServer((HOTE, PORT), H).serve_forever()
