# Captures de secours pour les projets sans image dans le README :
# 1) image d'aperçu personnalisée du dépôt GitHub (usesCustomOpenGraphImage), 2) og:image de la page de démo.
import hashlib, html, io, json, re, subprocess, urllib.parse, urllib.request
from PIL import Image
P = json.load(open('data/projets_brut.json'))
G = {x['url']: x for x in json.load(open('data/github.json'))}
UA = 'Mozilla/5.0 (oshf-showcase vignettes)'
def get(u, n=15_000_000):
    with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': UA}), timeout=30) as r:
        return r.read(n)
def sauve(p, data, source):
    im = Image.open(io.BytesIO(data)); im.load()
    w, h = im.size
    if w < 320 or h < 160: return False
    im = im.convert('RGB'); im.thumbnail((640, 2000))
    nom = hashlib.sha1(G[p['url']]['cle'].encode()).hexdigest()[:12] + '.webp'
    im.save(f'public/shots/{nom}', 'WEBP', quality=78)
    p['capture'] = {'fichier': f'shots/{nom}', 'source': source, 'genre': 'apercu', 'taille': list(im.size)}
    return True
n = 0
for p in P:
    if p['capture'] or not p['depot_trouve']: continue
    g = G[p['url']].get('github') or {}
    o, r = g['nom'].split('/')
    q = 'query{repository(owner:"%s",name:"%s"){usesCustomOpenGraphImage openGraphImageUrl}}' % (o, r)
    res = subprocess.run(['gh', 'api', 'graphql', '-f', f'query={q}'], capture_output=True, text=True)
    try:
        d = json.loads(res.stdout)['data']['repository']
        if d['usesCustomOpenGraphImage'] and sauve(p, get(d['openGraphImageUrl']), d['openGraphImageUrl']):
            n += 1; continue
    except Exception as e:
        pass
    if p['demo']:
        try:
            t = get(p['demo'], 2_000_000).decode('utf-8', 'replace')
            m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', t) or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image', t)
            if m:
                u = urllib.parse.urljoin(p['demo'], html.unescape(m.group(1)))
                if sauve(p, get(u), u): n += 1
        except Exception:
            pass
import urllib.parse
# descriptions qui ne sont qu'une adresse : remplacées par le premier paragraphe du README
for p in P:
    if re.fullmatch(r'https?://\S+', p['description'] or ''):
        p['description'] = ''
json.dump(P, open('data/projets_brut.json', 'w'), indent=1, ensure_ascii=False)
print('captures ajoutées', n, 'total avec capture', sum(1 for p in P if p['capture']))
