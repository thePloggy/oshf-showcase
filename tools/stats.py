# Étoiles, forks (API GitHub), téléchargements des fichiers de release (API GitHub) et installations du registre ComfyUI (api.comfy.org).
import json, re, subprocess, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
G = json.load(open('data/github.json'))
# registre ComfyUI complet, indexé par dépôt
reg, page = {}, 1
while True:
    req = urllib.request.Request(f'https://api.comfy.org/nodes?page={page}&limit=100', headers={'User-Agent': 'oshf-showcase/0.1'})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    for n in d['nodes']:
        r = (n.get('repository') or '').lower().rstrip('/').removesuffix('.git')
        if r: reg[r] = {'id': n['id'], 'installations': n.get('downloads')}
    if page >= d['totalPages']: break
    page += 1; time.sleep(0.3)
print('registre', len(reg))
def gh(p):
    r = subprocess.run(['gh', 'api', p], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None
def un(it):
    g = it.get('github') or {}
    if 'nom' not in g: return it['cle'], None
    d = gh(f"repos/{g['nom']}") or {}
    rel = gh(f"repos/{g['nom']}/releases?per_page=100") or []
    dl = sum(a.get('download_count', 0) for r in rel for a in r.get('assets', []))
    rg = reg.get(f"https://github.com/{g['nom']}".lower())
    return it['cle'], {'etoiles': d.get('stargazers_count'), 'forks': d.get('forks_count'), 'releases': len(rel),
                       'telechargements_releases': dl if rel else None, 'registre_comfy': rg}
with ThreadPoolExecutor(6) as ex:
    S = dict(ex.map(un, G))
json.dump({'releve': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'stats': S}, open('data/stats.json', 'w'), indent=1)
v = [s for s in S.values() if s]
print('avec releases', sum(1 for s in v if s['releases']), 'téléchargements>0', sum(1 for s in v if s['telechargements_releases']), 'au registre', sum(1 for s in v if s['registre_comfy']))
