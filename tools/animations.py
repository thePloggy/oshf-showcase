# Animations des cartes, dans cet ordre de préférence :
#   1. un GIF animé du README (la « home » du dépôt) ;
#   2. sinon un GIF animé trouvé ailleurs dans le dépôt ;
#   3. sinon l'image fixe déjà retenue (images.py) ;
#   4. sinon une capture de la page GitHub du dépôt ;
#   5. sinon rien (la carte affiche des initiales).
# Un GIF est converti en courte vidéo MP4 muette (480 px, 8 s au plus, 12 i/s) + une affiche WebP.
# Sortie : data/animations.json, public/anim/, public/shots/.
import hashlib, io, json, os, re, subprocess, sys, tempfile, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from images import candidats, readme, telecharge, UA   # noqa: E402

os.makedirs('public/anim', exist_ok=True)
G = {x['cle']: x for x in json.load(open('data/github.json'))}
P = json.load(open('data/projets_brut.json'))
CLE = {x['url']: x['cle'] for x in G.values()}
BONUS = re.compile(r'demo|hero|preview|screen|showcase|overview|teaser|tour|app|studio|ui', re.I)
MAXO = 60_000_000


def gh(path):
    r = subprocess.run(['gh', 'api', path], capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 else None


def anime(data):
    try:
        im = Image.open(io.BytesIO(data))
        return getattr(im, 'is_animated', False) and im.n_frames > 3 and im.size[0] >= 240 and im.size[1] >= 135
    except Exception:
        return False


def convertit(data, ident):
    """GIF -> MP4 court + affiche. Renvoie (anim, affiche, taille) ou None."""
    with tempfile.NamedTemporaryFile(suffix='.gif') as f:
        f.write(data); f.flush()
        mp4, aff = f'public/anim/{ident}.mp4', f'public/shots/{ident}.webp'
        vf = "fps=12,scale='min(480,iw)':-2:flags=lanczos,format=yuv420p"
        r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f.name, '-t', '8', '-an', '-vf', vf, '-c:v', 'libx264', '-crf', '30',
                            '-preset', 'slow', '-movflags', '+faststart', mp4], capture_output=True, timeout=180)
        if r.returncode or not os.path.exists(mp4) or os.path.getsize(mp4) < 2000:
            return None
        im = Image.open(io.BytesIO(data))
        try:
            im.seek(min(im.n_frames - 1, max(0, im.n_frames // 6)))   # une image un peu après le début
        except Exception:
            pass
        im = im.convert('RGB'); im.thumbnail((640, 2000)); im.save(aff, 'WEBP', quality=78)
        return f'anim/{ident}.mp4', f'shots/{ident}.webp', list(im.size)


def gif_du_readme(it):
    for u in candidats(it, readme(it))[:10]:
        if not (re.search(r'\.gif(\?|$)', u, re.I) or 'user-attachments' in u or 'user-images' in u):
            continue
        try:
            ct, data = telecharge(u, MAXO)
        except Exception:
            continue
        if anime(data):
            return u, data
    return None


def gif_du_depot(g):
    t = gh(f"repos/{g['nom']}/git/trees/{g['branche']}?recursive=1")
    if not t:
        return None
    gifs = [x for x in t.get('tree', []) if x.get('type') == 'blob' and x['path'].lower().endswith('.gif') and 150_000 <= x.get('size', 0) <= MAXO
            and not re.search(r'node_modules|/vendor/|logo|icon|badge|spinner|loading', x['path'], re.I)]
    gifs.sort(key=lambda x: (not BONUS.search(x['path']), -x['size']))
    for x in gifs[:3]:
        u = f"https://raw.githubusercontent.com/{g['nom']}/{g['branche']}/{urllib.request.quote(x['path'])}"
        try:
            ct, data = telecharge(u, MAXO)
        except Exception:
            continue
        if anime(data):
            return u, data
    return None


def capture_github(g, ident):
    """Capture de la page du dépôt, quand il n'a ni GIF ni image."""
    png = f'/tmp/oshf_gh_{ident}.png'
    try:
        subprocess.run(['google-chrome', '--headless=new', '--disable-gpu', '--hide-scrollbars', '--virtual-time-budget=8000', '--window-size=1280,860',
                        f'--screenshot={png}', f"https://github.com/{g['nom']}"], capture_output=True, timeout=90)
        im = Image.open(png).convert('RGB')
        if im.size[0] < 800:
            return None
        im.thumbnail((640, 2000)); aff = f'shots/{ident}.webp'; im.save('public/' + aff, 'WEBP', quality=80)
        return aff, list(im.size)
    except Exception:
        return None
    finally:
        if os.path.exists(png):
            os.remove(png)


def un(p):
    g = G[CLE[p['url']]].get('github') or {}
    if 'nom' not in g:
        return p['id'], {'niveau': 'initiales'}
    ident = hashlib.sha1(CLE[p['url']].encode()).hexdigest()[:12]
    it = G[CLE[p['url']]]
    for niveau, f in (('gif_readme', lambda: gif_du_readme(it)), ('gif_depot', lambda: gif_du_depot(g))):
        try:
            r = f()
        except Exception:
            r = None
        if r:
            c = convertit(r[1], ident)
            if c:
                return p['id'], {'niveau': niveau, 'source': r[0], 'anim': c[0], 'affiche': c[1], 'taille': c[2]}
    if p['capture']:
        return p['id'], {'niveau': 'image'}
    return p['id'], {'niveau': 'initiales', 'a_capturer': True}


if __name__ == '__main__':
    with ThreadPoolExecutor(6) as ex:
        A = dict(ex.map(un, P))
    # captures de page GitHub : une à la fois (navigateur sans interface)
    for p in P:
        a = A[p['id']]
        if a.pop('a_capturer', False):
            g = G[CLE[p['url']]]['github']
            c = capture_github(g, hashlib.sha1(CLE[p['url']].encode()).hexdigest()[:12])
            if c:
                A[p['id']] = {'niveau': 'capture_github', 'affiche': c[0], 'taille': c[1]}
    json.dump(A, open('data/animations.json', 'w'), indent=1, ensure_ascii=False)
    import collections
    print(dict(collections.Counter(a['niveau'] for a in A.values())))
    print('poids des animations :', round(sum(os.path.getsize('public/' + a['anim']) for a in A.values() if a.get('anim')) / 1e6, 1), 'Mo')
