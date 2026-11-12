'use strict';
// Vitrine #OpenSourceHiggsfield : grille aléatoire, filtres par fonction, vote à 10 points.
const CATS = [
  ['all', 'All'],
  ['studio', 'All-in-one studios'],
  ['film', 'Film & series pipelines'],
  ['swap', 'Character swap & recast'],
  ['camera', 'Camera, reshoot & reframe'],
  ['vfx', 'VFX & effects'],
  ['3d', '3D, splats & previs'],
  ['audio', 'Music, audio & lip-sync'],
  ['ads', 'Ads & product'],
  ['character', 'Characters & datasets'],
  ['edit', 'Editors, canvases & agents'],
  ['tools', 'Nodes & tools'],
  ['fun', 'Games & experiences'],
  ['other', 'Other / repo unavailable'],
];
const CAT_LABEL = Object.fromEntries(CATS);
const ICON = {
  star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
  fork: '<circle cx="12" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9v2c0 .6-.4 1-1 1H7c-.6 0-1-.4-1-1V9"/><path d="M12 12v3"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
  package: '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
  github: '<path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/>',
  link: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  play: '<polygon points="6 3 20 12 6 21 6 3"/>',
  minus: '<path d="M5 12h14"/>',
  plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
};
const svg = (k) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICON[k]}</svg>`;
const $ = (s) => document.querySelector(s);
// Sur GitHub Pages, l'API de vote est servie par forge ; en local, par le même serveur que la page.
const API = location.hostname.endsWith('github.io') ? 'https://forge.taila06702.ts.net:10000' : '';
const fmt = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 });

let PROJECTS = [], ORDER = {}, STATE = { totals: {}, mine: {}, left: 10, budget: 10, voters: 0 };
let filtre = 'all', recherche = '', tri = 'random', mesVotes = false;
const cartes = new Map();

function melange() {
  const ids = PROJECTS.map((p) => p.id);
  for (let i = ids.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [ids[i], ids[j]] = [ids[j], ids[i]];
  }
  ORDER = Object.fromEntries(ids.map((id, i) => [id, i]));
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text != null) e.textContent = text;
  return e;
}

function lien(href, label, icon, cls) {
  if (!/^https?:\/\//i.test(href || '')) return document.createTextNode('');
  const a = el('a', cls || '');
  a.href = href; a.target = '_blank'; a.rel = 'noopener noreferrer nofollow';
  a.innerHTML = svg(icon);
  a.append(document.createTextNode(label));
  return a;
}

function initiales(t) {
  return t.replace(/[^\p{L}\p{N} ]/gu, ' ').split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('') || '?';
}

// Les animations ne jouent que dans la zone visible ; avec « réduire les animations », seule l'affiche est montrée.
const CALME = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const VUES = new IntersectionObserver((entrees) => {
  for (const e of entrees) {
    const v = e.target;
    if (e.isIntersecting && !CALME) {
      if (!v.src) v.src = v.dataset.src;
      v.play().catch(() => {});
    } else if (!v.paused) v.pause();
  }
}, { rootMargin: '200px 0px', threshold: 0.15 });

function carte(p) {
  const c = el('article', 'card');
  c.dataset.id = p.id;
  const shot = el('div', 'shot' + (p.shot ? '' : ' none'));
  if (p.shot && p.anim) {
    // animation du projet : courte vidéo muette en boucle, lancée seulement quand la carte est à l'écran
    const v = el('video');
    v.muted = true; v.loop = true; v.playsInline = true; v.preload = 'none';
    v.poster = p.shot.src; v.dataset.src = p.anim;
    v.width = p.shot.w; v.height = p.shot.h;
    v.setAttribute('aria-label', `Animated preview of ${p.title}`);
    v.title = `Animation from the ${p.title} repository, by ${p.author}`;
    shot.append(v);
    VUES.observe(v);
  } else if (p.shot) {
    const img = el('img');
    img.src = p.shot.src; img.alt = `Screenshot of ${p.title}`;
    img.title = p.shot_kind === 'capture_github' ? `GitHub page of ${p.title}` : `Image from the ${p.title} README, by ${p.author}`;
    img.loading = 'lazy'; img.decoding = 'async';
    img.width = p.shot.w; img.height = p.shot.h;
    shot.append(img);
  } else {
    shot.textContent = initiales(p.title);
    shot.setAttribute('aria-hidden', 'true');
  }
  shot.append(el('span', 'tag', CAT_LABEL[p.category] || p.category));
  c.append(shot);

  const b = el('div', 'body');
  b.append(el('h2', '', p.title));
  b.append(el('p', 'author', `by ${p.author}`));
  if (p.aka && p.aka.length) b.append(el('p', 'aka', `Also submitted as ${p.aka.join(', ')}`));
  if (!p.found) b.append(el('span', 'missing', 'Repository not reachable on 12 Nov 2026'));
  if (p.description) b.append(el('p', 'desc', p.description));

  const st = el('div', 'stats');
  const stat = (icon, v, label) => {
    if (v == null) return;
    const s = el('span'); s.title = label; s.setAttribute('aria-label', `${v} ${label}`);
    s.innerHTML = svg(icon); s.append(document.createTextNode(fmt.format(v)));
    st.append(s);
  };
  stat('star', p.stars, 'GitHub stars');
  stat('fork', p.forks, 'forks');
  if (p.release_downloads) stat('download', p.release_downloads, 'release downloads');
  if (p.registry_installs) stat('package', p.registry_installs, 'installs from the Comfy Registry');
  if (st.childElementCount) b.append(st);

  const ls = el('div', 'links');
  const isGit = /github\.com|codeberg\.org/.test(p.url);
  ls.append(lien(p.url, isGit ? 'Code' : 'Website', isGit ? 'github' : 'link'));
  if (p.demo) ls.append(lien(p.demo, 'Demo', 'link', 'demo'));
  if (p.video) ls.append(lien(p.video, 'Video', 'play'));
  b.append(ls);

  const v = el('div', 'vote');
  const tot = el('span', 'total');
  const step = el('div', 'stepper');
  const moins = el('button', 'minus'); moins.type = 'button'; moins.innerHTML = svg('minus'); moins.setAttribute('aria-label', `Take one point back from ${p.title}`);
  const out = el('output'); out.setAttribute('aria-label', `Your points on ${p.title}`);
  const plus = el('button', 'plus'); plus.type = 'button'; plus.innerHTML = svg('plus'); plus.setAttribute('aria-label', `Give one point to ${p.title}`);
  moins.addEventListener('click', () => voter(p.id, -1));
  plus.addEventListener('click', () => voter(p.id, 1));
  step.append(moins, out, plus);
  v.append(tot, step);
  b.append(v);
  c.append(b);
  cartes.set(p.id, { c, tot, out, moins, plus });
  return c;
}

function majCarte(id) {
  const k = cartes.get(id);
  if (!k) return;
  const mine = STATE.mine[id] || 0, total = STATE.totals[id] || 0;
  k.tot.innerHTML = '';
  const bb = el('b', '', String(total));
  k.tot.append(bb, document.createTextNode(total === 1 ? ' point' : ' points'));
  k.out.textContent = String(mine);
  k.moins.disabled = mine <= 0;
  k.plus.disabled = STATE.left <= 0;
  k.c.classList.toggle('voted', mine > 0);
}

function majPortefeuille() {
  const d = $('#dots');
  d.innerHTML = '';
  for (let i = 0; i < STATE.budget; i++) d.append(el('i', i < STATE.left ? '' : 'used'));
  $('#left-label').textContent = STATE.left === 0 ? 'All 10 points placed' : `${STATE.left} point${STATE.left > 1 ? 's' : ''} left`;
  for (const id of cartes.keys()) majCarte(id);
  // "My votes" button: how many projects hold this visitor's points
  const n = Object.values(STATE.mine).filter((v) => v > 0).length;
  $('#mine-label').textContent = n ? `My votes (${n})` : 'My votes';
}

function toast(msg) {
  const t = $('#toast');
  t.textContent = msg; t.classList.add('on');
  clearTimeout(toast.h); toast.h = setTimeout(() => t.classList.remove('on'), 2200);
}

async function voter(id, delta) {
  try {
    const r = await fetch(API + '/api/vote', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id, delta }) });
    const d = await r.json();
    if (d.totals) { STATE = d; majPortefeuille(); }
    if (r.status === 409) toast(delta > 0 ? 'No points left: take one back from another project first.' : 'Nothing to take back here.');
    else if (r.status === 429) toast('Easy there, try again in a few seconds.');
    else if (!r.ok) toast('Vote not saved, please retry.');
    if (tri === 'points' || tri === 'mine' || mesVotes) rendu();
  } catch (e) {
    toast('Vote not saved: the server did not answer.');
  }
}

function correspond(p) {
  if (mesVotes && !(STATE.mine[p.id] > 0)) return false;
  if (filtre !== 'all' && p.category !== filtre) return false;
  if (!recherche) return true;
  const h = `${p.title} ${p.author} ${p.description} ${(p.aka || []).join(' ')} ${CAT_LABEL[p.category]}`.toLowerCase();
  return recherche.split(/\s+/).every((w) => h.includes(w));
}

function rendu() {
  const liste = PROJECTS.filter(correspond);
  const cmp = {
    random: (a, b) => ORDER[a.id] - ORDER[b.id],
    points: (a, b) => (STATE.totals[b.id] || 0) - (STATE.totals[a.id] || 0) || ORDER[a.id] - ORDER[b.id],
    stars: (a, b) => (b.stars || 0) - (a.stars || 0) || ORDER[a.id] - ORDER[b.id],
    mine: (a, b) => (STATE.mine[b.id] || 0) - (STATE.mine[a.id] || 0) || ORDER[a.id] - ORDER[b.id],
    az: (a, b) => a.title.localeCompare(b.title, 'en', { sensitivity: 'base' }),
  }[tri];
  liste.sort(cmp);
  const g = $('#grid');
  g.replaceChildren(...liste.map((p) => cartes.get(p.id).c));
  $('#count').textContent = `${liste.length} project${liste.length > 1 ? 's' : ''}${mesVotes ? ' you gave points to' : ''}${filtre !== 'all' ? ` in ${CAT_LABEL[filtre]}` : ''}`;
  $('#empty').textContent = mesVotes && !Object.values(STATE.mine).some((v) => v > 0)
    ? 'You have not given any points yet. Use the + button on a project you like.'
    : mesVotes ? 'None of the projects you voted for matches this filter.' : 'No project matches this search.';
  $('#empty').hidden = liste.length > 0;
}

function puces() {
  const n = { all: PROJECTS.length };
  for (const p of PROJECTS) n[p.category] = (n[p.category] || 0) + 1;
  const nav = $('#chips');
  for (const [k, label] of CATS) {
    if (!n[k]) continue;
    const b = el('button', 'chip'); b.type = 'button';
    b.setAttribute('aria-pressed', String(k === filtre));
    b.append(document.createTextNode(label));
    b.append(el('span', 'n', String(n[k])));
    b.addEventListener('click', () => {
      filtre = k;
      nav.querySelectorAll('.chip').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
      rendu();
    });
    nav.append(b);
  }
}

async function demarre() {
  const d = await (await fetch('projects.json')).json();
  PROJECTS = d.projects;
  melange();
  for (const p of PROJECTS) carte(p);
  puces();
  const date = new Date(d.updated.replace(/(\d{2})(\d{2})$/, '$1:$2'));
  $('#foot').textContent = `${PROJECTS.length} projects from the three #OpenSourceHiggsfield submission threads (duplicate links merged). Stars, forks and release downloads from the GitHub API; installs from the Comfy Registry; snapshot of ${date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}. Previews are reduced copies of a GIF or an image from each project's repository (or a capture of its GitHub page when it has none), credited to and linked with that project; to have yours removed or changed, open an issue on github.com/thePloggy/oshf-showcase. Categories are indicative. One vote budget of 10 points per IP address. Visits are counted anonymously (no cookies, no raw IP stored).`;
  try {
    const r = await fetch(API + '/api/state?visit=1');
    if (!r.ok) throw new Error(r.status);
    STATE = await r.json();
  } catch (e) {
    document.body.classList.add('no-votes');
  }
  majPortefeuille();
  if (document.body.classList.contains('no-votes')) $('#left-label').textContent = 'Voting is offline right now';
  rendu();
  let h;
  $('#q').addEventListener('input', (e) => { clearTimeout(h); h = setTimeout(() => { recherche = e.target.value.trim().toLowerCase(); rendu(); }, 120); });
  $('#sort').addEventListener('change', (e) => { tri = e.target.value; rendu(); });
  $('#mine').addEventListener('click', (e) => {
    mesVotes = !mesVotes;
    e.currentTarget.setAttribute('aria-pressed', String(mesVotes));
    rendu();
    window.scrollTo({ top: 0, behavior: CALME ? 'auto' : 'smooth' });
  });
  $('#reshuffle').addEventListener('click', () => { melange(); tri = 'random'; $('#sort').value = 'random'; rendu(); });
  setInterval(async () => {
    try {
      const r = await fetch(API + '/api/state');
      if (r.ok) { STATE = await r.json(); document.body.classList.remove('no-votes'); majPortefeuille(); }
    } catch (e) { /* hors ligne */ }
  }, 30000);
}
// filtres : cliquer-glisser pour faire défiler la rangée (souris) ; le tactile garde son défilement natif
(() => {
  const nav = $('#chips');
  let x0 = 0, s0 = 0, actif = false, bouge = false;
  nav.addEventListener('pointerdown', (e) => {
    if (e.pointerType !== 'mouse' || e.button !== 0) return;
    actif = true; bouge = false; x0 = e.clientX; s0 = nav.scrollLeft;
  });
  window.addEventListener('pointermove', (e) => {
    if (!actif) return;
    const dx = e.clientX - x0;
    if (!bouge && Math.abs(dx) > 5) { bouge = true; nav.classList.add('drag'); }
    if (bouge) nav.scrollLeft = s0 - dx;
  });
  const fin = () => { if (!actif) return; actif = false; setTimeout(() => nav.classList.remove('drag'), 0); };
  window.addEventListener('pointerup', fin);
  window.addEventListener('pointercancel', fin);
  // un glissement ne doit pas compter comme un clic sur un filtre
  nav.addEventListener('click', (e) => { if (bouge) { e.stopPropagation(); e.preventDefault(); bouge = false; } }, true);
  // molette verticale = défilement horizontal de la rangée
  nav.addEventListener('wheel', (e) => {
    if (Math.abs(e.deltaY) > Math.abs(e.deltaX) && nav.scrollWidth > nav.clientWidth) { nav.scrollLeft += e.deltaY; e.preventDefault(); }
  }, { passive: false });
})();
demarre();
