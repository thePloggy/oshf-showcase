# Pour chaque projet : choisit une capture dans le README (image, image animée, ou image d'une vidéo),
# la réduit en vignette WebP 640 px, et relève les liens de démo et de vidéo. Sortie : data/projets.json + public/shots/.
import hashlib, html, io, json, os, re, subprocess, tempfile, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

UA = 'oshf-showcase/0.1 (vignettes de dépôts publics)'
os.makedirs('public/shots', exist_ok=True)
L = json.load(open('data/github.json'))

EXCLUS = re.compile(r'shields\.io|badgen|badge|travis-ci|codecov|star-history|contrib\.rocks|buymeacoffee|ko-fi|discord|divider|/logo|logo\.|icon|favicon|avatars\.githubusercontent|komarev|visitor|hits\.|api\.star', re.I)
BONUS = re.compile(r'screen|shot|demo|hero|preview|ui[-_.]|app|studio|tour|interface|example|result|showcase|overview|teaser', re.I)


def readme(it):
    f = f"data/readme/{it['cle'].replace('/', '__')}.md"
    return open(f).read() if os.path.exists(f) else ''


def base_raw(it):
    g = it['github']
    d = os.path.dirname(g.get('readme_chemin', ''))
    return f"https://raw.githubusercontent.com/{g['nom']}/{g['branche']}/" + (d + '/' if d else '')


def candidats(it, txt):
    out = []
    for m in re.finditer(r'!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\s*\)|<img[^>]+?src=["\']([^"\']+)["\']|<video[^>]+?src=["\']([^"\']+)["\']|(https://github\.com/user-attachments/assets/[a-f0-9-]+)|(https://(?:private-)?user-images\.githubusercontent\.com/\S+?\.(?:png|jpe?g|gif|webp|mp4|mov))', txt, re.I):
        u = next(g for g in m.groups() if g)
        u = html.unescape(u)
        if EXCLUS.search(u):
            continue
        if not re.match(r'https?://', u):
            if not it.get('github') or 'nom' not in it['github']:
                continue
            u = urllib.parse.urljoin(base_raw(it), u.lstrip('./') if not u.startswith('/') else u[1:])
        u = re.sub(r'https://github\.com/([^/]+)/([^/]+)/blob/', r'https://raw.githubusercontent.com/\1/\2/', u)
        if u.lower().endswith('.svg'):
            continue
        if u not in out:
            out.append(u)
    for m in re.finditer(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|img\.youtube\.com/vi/)([A-Za-z0-9_-]{11})', txt):
        u = f'https://img.youtube.com/vi/{m.group(1)}/hqdefault.jpg'
        if u not in out:
            out.append(u)
    return out


def telecharge(u, maxo=40_000_000):
    req = urllib.request.Request(u, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        ct = r.headers.get('Content-Type', '')
        data = r.read(maxo + 1)
    if len(data) > maxo:
        raise ValueError('trop gros')
    return ct, data


def image_de(ct, data):
    if 'video' in ct or data[4:8] in (b'ftyp',) or data[:4] == b'\x1aE\xdf\xa3':
        with tempfile.NamedTemporaryFile(suffix='.vid') as f, tempfile.NamedTemporaryFile(suffix='.png') as g:
            f.write(data); f.flush()
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '1', '-i', f.name, '-frames:v', '1', g.name], timeout=60)
            if os.path.getsize(g.name) == 0:
                subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f.name, '-frames:v', '1', g.name], timeout=60)
            im = Image.open(g.name); im.load(); return im, 'video'
    im = Image.open(io.BytesIO(data)); im.load()
    return im, 'image'


def choisit(it):
    txt = readme(it)
    cands = candidats(it, txt)[:8]
    essais, retenu = [], None
    ok = []
    for u in cands:
        try:
            ct, data = telecharge(u)
            im, genre = image_de(ct, data)
            w, h = im.size
            bon = w >= 320 and h >= 180 and 0.35 <= w / h <= 3.2
            essais.append({'url': u, 'taille': [w, h], 'retenue_possible': bon})
            if bon:
                ok.append((u, im, genre))
                if BONUS.search(u) or len(ok) >= 1 and not cands.index(u) == 0:
                    pass
        except Exception as e:
            essais.append({'url': u, 'erreur': type(e).__name__})
        if len(ok) >= 3:
            break
    if ok:
        # priorité à une image dont le nom évoque une capture d'écran, sinon la première valable
        u, im, genre = next((x for x in ok if BONUS.search(x[0])), ok[0])
        im = im.convert('RGB')
        im.thumbnail((640, 2000))
        nom = hashlib.sha1(it['cle'].encode()).hexdigest()[:12] + '.webp'
        im.save(f'public/shots/{nom}', 'WEBP', quality=78)
        retenu = {'fichier': f'shots/{nom}', 'source': u, 'genre': genre, 'taille': list(im.size)}
    return retenu, essais


def liens(it, txt):
    g = it.get('github') or {}
    demo, video = None, None
    hp = (g.get('homepage') or '').strip()
    if hp and 'github.com' not in hp:
        demo = hp if hp.startswith('http') else 'https://' + hp
    if not demo:
        for m in re.finditer(r'\[([^\]]{0,80})\]\((https?://[^)\s]+)\)', txt):
            t, u = m.groups()
            if EXCLUS.search(u) or 'github.com' in u:
                continue
            if re.search(r'\bdemo\b|live|try it|playground|app', t, re.I) or re.search(r'huggingface\.co/spaces|vercel\.app|netlify\.app|github\.io|\.pages\.dev|onrender\.com', u):
                if not re.search(r'youtu', u):
                    demo = u; break
    m = re.search(r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[A-Za-z0-9_-]{11}', txt)
    if m:
        video = m.group(0)
    return demo, video


def texte_brut(md):
    md = re.sub(r'<!--.*?-->', ' ', md, flags=re.S)
    md = re.sub(r'```.*?```', ' ', md, flags=re.S)
    for bloc in re.split(r'\n\s*\n', md):
        b = bloc.strip()
        if not b or b.startswith(('#', '!', '<', '|', '[!', '---', '>')) or len(b) < 60:
            continue
        b = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', b)
        b = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', b)
        b = re.sub(r'<[^>]+>|[*_`]', '', b)
        b = re.sub(r'\s+', ' ', b).strip()
        if len(b) >= 60 and not re.fullmatch(r'https?://\S+', b):
            return b
    return ''


def court(t, n=240):
    t = re.sub(r'\s+', ' ', t or '').strip()
    return t if len(t) <= n else t[:n].rsplit(' ', 1)[0] + '…'


def un(it):
    txt = readme(it)
    g = it.get('github') or {}
    trouve = 'nom' in g
    shot, essais = choisit(it) if trouve else (None, [])
    demo, video = liens(it, txt) if trouve else (None, None)
    desc = g.get('description') or texte_brut(txt)
    auteur = re.sub(r'^(.+?) by \1$', r'\1', it['auteur'])
    return {'id': hashlib.sha1(it['cle'].encode()).hexdigest()[:10], 'titre': it['titre'], 'autres_titres': it.get('autres_titres', []),
            'auteur': auteur, 'url': it['url'], 'depot_trouve': trouve, 'description': court(desc), 'etoiles': g.get('etoiles'),
            'demo': demo, 'video': video, 'capture': shot, 'essais_capture': essais, 'topics': g.get('topics') or []}


if __name__ == '__main__':
    with ThreadPoolExecutor(6) as ex:
        P = list(ex.map(un, L))
    json.dump(P, open('data/projets_brut.json', 'w'), indent=1, ensure_ascii=False)
    print('projets', len(P), 'avec capture', sum(1 for p in P if p['capture']), 'dont vidéo', sum(1 for p in P if p['capture'] and p['capture']['genre'] == 'video'),
          'démo', sum(1 for p in P if p['demo']), 'vidéo', sum(1 for p in P if p['video']), 'sans description', sum(1 for p in P if not p['description']))
