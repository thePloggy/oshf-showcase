# Assemble public/projects.json à partir des données récoltées (aucune donnée privée).
import json
P = json.load(open('data/projets_brut.json'))
C = json.load(open('data/categories.json'))
S = json.load(open('data/stats.json'))
G = {x['cle']: x for x in json.load(open('data/github.json'))}
CLES = {x['url']: x['cle'] for x in G.values()}
# deux pages hors GitHub : description relevée sur leur site
import os
ANIM = json.load(open('data/animations.json')) if os.path.exists('data/animations.json') else {}
EXTRA = {'PlainSight': 'Photo + script to a talking vertical ad in one ComfyUI graph, with TeethLock temporal teeth repair. Open source, open weights, runs on a CPU.',
         'Manga Coloring Tool 2': 'High-performance AI manga colorization suite powered by FLUX.2 Klein 4B: React UI, style reference transfer, HD reader, 1-click CBZ export. 100% local.'}
out = []
for p in P:
    st = S['stats'].get(CLES[p['url']]) or {}
    rg = st.get('registre_comfy') or {}
    an = ANIM.get(p['id']) or {}
    out.append({
        'id': p['id'], 'title': p['titre'].replace('Lip Servic', 'Lip Service') if p['titre'] == 'Lip Servic' else p['titre'],
        'aka': [t for t in p['autres_titres'] if t != 'Lip Service'], 'author': p['auteur'], 'url': p['url'],
        'found': p['depot_trouve'] or p['titre'] in EXTRA, 'description': p['description'] or EXTRA.get(p['titre'], ''),
        'category': C[p['id']], 'demo': p['demo'], 'video': p['video'],
        'shot': ({'src': an['affiche'], 'w': an['taille'][0], 'h': an['taille'][1]} if an.get('affiche')
                 else {'src': p['capture']['fichier'], 'w': p['capture']['taille'][0], 'h': p['capture']['taille'][1]} if p['capture'] else None),
        'anim': an.get('anim'), 'shot_kind': an.get('niveau'),
        'stars': st.get('etoiles'), 'forks': st.get('forks'), 'release_downloads': st.get('telechargements_releases'),
        'registry_installs': rg.get('installations'), 'registry_id': rg.get('id'),
    })
json.dump({'updated': S['releve'], 'projects': out}, open('public/projects.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print(len(out), 'projets ; repo introuvable :', sum(not x['found'] for x in out))
