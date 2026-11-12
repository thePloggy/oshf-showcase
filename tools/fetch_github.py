# Récupère pour chaque dépôt : description, homepage, étoiles, branche, README (texte brut). Lecture seule, API GitHub via gh.
import json, re, subprocess, base64, os, sys
from concurrent.futures import ThreadPoolExecutor
L = json.load(open('data/liste.json'))
os.makedirs('data/readme', exist_ok=True)
def gh(path):
    r = subprocess.run(['gh', 'api', path], capture_output=True, text=True)
    if r.returncode: return None, r.stderr.strip()[:200]
    return json.loads(r.stdout), None
def un(it):
    m = re.match(r'https://github\.com/([^/]+)/([^/#?]+)(?:/tree/([^/#?]+)/?([^#?]*))?', it['url'])
    if not m:
        it['github'] = None; return it
    o, r, br, sub = m.group(1), m.group(2).removesuffix('.git'), m.group(3), (m.group(4) or '').strip('/')
    d, err = gh(f'repos/{o}/{r}')
    if not d:
        it['github'] = {'erreur': err}; return it
    br = br or d['default_branch']
    it['github'] = {'nom': d['full_name'], 'description': d.get('description'), 'homepage': d.get('homepage'),
                    'etoiles': d.get('stargazers_count'), 'branche': br, 'sous_dossier': sub, 'topics': d.get('topics'),
                    'cree': d.get('created_at'), 'pousse': d.get('pushed_at'), 'archive': d.get('archived'), 'og': d.get('owner', {}).get('avatar_url')}
    rd, err = gh(f'repos/{d["full_name"]}/readme/{sub}?ref={br}' if sub else f'repos/{d["full_name"]}/readme?ref={br}')
    if rd:
        txt = base64.b64decode(rd['content']).decode('utf-8', 'replace')
        it['github']['readme_chemin'] = rd['path']
        open(f"data/readme/{it['cle'].replace('/', '__')}.md", 'w').write(txt)
    else:
        it['github']['readme_erreur'] = err
    return it
with ThreadPoolExecutor(6) as ex:
    L = list(ex.map(un, L))
json.dump(L, open('data/github.json', 'w'), indent=1, ensure_ascii=False)
print('ok', sum(1 for x in L if x.get('github') and 'nom' in x['github']), 'erreurs', [x['titre'] for x in L if not x.get('github') or 'erreur' in x['github']])
print('sans readme', [x['titre'] for x in L if x.get('github') and 'nom' in x['github'] and 'readme_chemin' not in x['github']])
