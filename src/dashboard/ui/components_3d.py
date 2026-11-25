"""The three WebGL pieces (Three.js r160, pinned on jsDelivr), each a self-contained HTML document with a calm
static fallback that is always in the page and only hidden once the scene has really started.

1. hero_html        : cream glass knot on a deep ink panel, a few depth particles, a small cursor parallax.
2. money_flow_html  : 3D columns of the year-end running balance of each outlook; grow in, sway, drag to turn.
3. donut_html       : tilted 3D cost donut whose slices lift on hover.

Shared rules (the RUNTIME below): transparent background, pixel ratio capped at 2, one animation loop per scene
that only runs while the scene is on screen, the tab is visible and it is the most visible scene on the page
(so at most one scene animates at a time), everything disposed and every listener removed when the frame goes
away. No WebGL, a blocked download, reduced motion or use_3d=False all leave the static fallback; no error text.
"""
from __future__ import annotations

import html
import json

from dashboard.ui import copy as C
from dashboard.ui import theme as T

THREE_URL = "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js"
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?'
         'family=Inter:wght@400;500;600&family=Plus+Jakarta+Sans:wght@700;800&display=swap" rel="stylesheet">')

RUNTIME = r"""
const CFG = JSON.parse(document.getElementById('cfg').textContent), P = CFG.palette;
const root = document.getElementById('root'), stage = document.getElementById('stage');
const SID = CFG.id + '-' + Math.random().toString(36).slice(2, 8);
const bus = (() => { try { return (window.parent.__aiwi3d = window.parent.__aiwi3d || {r: {}}); } catch (e) { return {r: {}}; } })();
const reduced = () => { try { return matchMedia('(prefers-reduced-motion: reduce)').matches
  || !!window.parent.document.querySelector('.aiwi-still'); } catch (e) { return matchMedia('(prefers-reduced-motion: reduce)').matches; } };
const hasGL = () => { try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch (e) { return false; } };
const cleanups = [];
const on = (t, ev, fn, o) => { t.addEventListener(ev, fn, o); cleanups.push(() => t.removeEventListener(ev, fn, o)); };
let ratio = 0;
function eligible() {
  if (document.hidden || ratio <= 0) return false;
  let best = -1, id = null;
  for (const [k, v] of Object.entries(bus.r)) if (v > best || (v === best && k < id)) { best = v; id = k; }
  return id === SID;
}
function loop(frame) {
  let raf = 0, poll = 0, last = 0;
  const tick = (t) => { raf = 0; if (!eligible()) { sleep(); return; }
    const dt = Math.min((t - last) / 1000, 0.05); last = t; frame(dt, t / 1000); raf = requestAnimationFrame(tick); };
  const start = () => { if (raf) return; if (poll) { clearInterval(poll); poll = 0; } last = performance.now(); raf = requestAnimationFrame(tick); };
  const sleep = () => { if (!poll) poll = setInterval(() => { if (eligible()) start(); }, 400); };
  cleanups.push(() => { cancelAnimationFrame(raf); clearInterval(poll); });
  return { wake: () => (eligible() ? start() : sleep()) };
}
async function boot(build) {
  if (!CFG.use3d || reduced() || !hasGL()) return;
  let THREE;
  const shared = (() => { try { return window.parent; } catch (e) { return window; } })();
  if (shared.__aiwi3dFailed) return;                       // the library could not be fetched earlier: stay still
  try { THREE = await import(CFG.three); } catch (e) { try { shared.__aiwi3dFailed = true; } catch (_) {} return; }
  let api;
  try {
    const renderer = new THREE.WebGLRenderer({alpha: true, antialias: true, powerPreference: 'high-performance'});
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    stage.appendChild(renderer.domElement);
    api = build(THREE, renderer);
    const size = () => { const w = stage.clientWidth, h = stage.clientHeight; if (!w || !h) return;
      renderer.setSize(w, h, false); api.resize(w, h); api.frame(0, performance.now() / 1000, true); };
    size();
    const ro = new ResizeObserver(size); ro.observe(stage); cleanups.push(() => ro.disconnect());
    const lp = loop((dt, t) => api.frame(dt, t, false));
    const io = new IntersectionObserver(es => { for (const e of es) { ratio = e.isIntersecting ? e.intersectionRatio : 0; }
      bus.r[SID] = ratio; lp.wake(); }, {threshold: [0, 0.05, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1]});
    io.observe(stage); cleanups.push(() => io.disconnect());
    on(document, 'visibilitychange', () => lp.wake());
    cleanups.push(() => { delete bus.r[SID]; if (api.dispose) api.dispose();
      renderer.dispose(); renderer.forceContextLoss && renderer.forceContextLoss(); renderer.domElement.remove(); });
    root.classList.add('live');
  } catch (e) { cleanups.splice(0).reverse().forEach(f => { try { f(); } catch (_) {} }); stage.innerHTML = ''; return; }
}
on(window, 'pagehide', () => cleanups.splice(0).reverse().forEach(f => { try { f(); } catch (_) {} }));
function disposeAll(scene) { scene.traverse(o => { if (o.geometry) o.geometry.dispose();
  const m = o.material; if (m) (Array.isArray(m) ? m : [m]).forEach(x => { if (x.map) x.map.dispose(); x.dispose(); }); }); }
function studioEnv(THREE, renderer, tint) {
  const env = new THREE.Scene(), pm = new THREE.PMREMGenerator(renderer);
  const sky = new THREE.Mesh(new THREE.SphereGeometry(10, 32, 16), new THREE.MeshBasicMaterial({color: tint, side: THREE.BackSide}));
  env.add(sky);
  [[0, 6, 0, 0xffffff, 6], [-6, 1, 3, 0x9fe8de, 4], [6, 0, -2, 0xc4b5fd, 4]].forEach(([x, y, z, c, s]) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(s, s), new THREE.MeshBasicMaterial({color: c, side: THREE.DoubleSide}));
    m.position.set(x, y, z); m.lookAt(0, 0, 0); env.add(m); });
  const tex = pm.fromScene(env, 0.035).texture; disposeAll(env); pm.dispose(); return tex;
}
const ease = p => 1 - Math.pow(1 - Math.min(Math.max(p, 0), 1), 3);
"""


def _doc(cfg: dict, css: str, body: str, script: str) -> str:
    live = bool(cfg.get("use3d"))
    cfg_json = json.dumps(cfg).replace("</", "<\\/")
    # the still version carries no script at all: no settings block, no download address
    run = (f'<script type="application/json" id="cfg">{cfg_json}</script><script type="module">{RUNTIME}\n{script}</script>'
           if live else "")
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8">{FONTS}<style>'
            f'html,body{{margin:0;background:transparent;font-family:{T.FONT};color:{cfg["palette"]["text"]};'
            f'-webkit-font-smoothing:antialiased;overflow:hidden}}*{{box-sizing:border-box}}'
            f'#stage{{position:absolute;inset:0}}#stage canvas{{display:block;width:100%!important;height:100%!important}}'
            f'.live .fallback{{display:none}}.sr{{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}}'
            f'{css}</style></head><body>{body}{run}</body></html>')


def _hex(c: str) -> str:
    return c if c.startswith("#") else "#4F46E5"


# ------------------------------------------------------------------------------------------------ 1. hero
def hero_html(use_3d: bool = True, palette: dict | None = None, sub: str | None = None) -> str:
    """Hero block. With use_3d=False (or reduced motion, or a failed download) only the CSS version shows."""
    p = palette or T.scene_palette("light")
    dark = p["mode"] == "dark"
    # a deep ink panel with one warm light, in both themes (no purple-to-teal glow)
    grad = ("radial-gradient(120% 140% at 88% 30%,#2A3550 0%,#161D2B 55%,#10151F 100%)" if dark
            else "radial-gradient(120% 140% at 88% 30%,#2C3B5E 0%,#1C2638 55%,#161E2D 100%)")
    css = f"""
.hero{{position:relative;height:280px;border-radius:16px;overflow:hidden;color:#F6F1E8;background:{grad}}}
.hero::before{{content:"";position:absolute;right:-8%;top:-30%;width:55%;height:160%;
  background:radial-gradient(closest-side,rgba(232,163,61,.22),transparent);pointer-events:none}}
.hero::after{{content:"";position:absolute;left:48px;bottom:34px;width:64px;height:3px;border-radius:2px;background:#E8A33D}}
.scrim{{position:absolute;inset:0;z-index:1;pointer-events:none;
  background:linear-gradient(90deg,rgba(16,21,31,.55) 0%,rgba(16,21,31,.2) 50%,transparent 72%)}}
.copy{{position:relative;z-index:2;padding:44px 48px;max-width:640px;will-change:transform;transition:transform .6s cubic-bezier(.22,.8,.24,1)}}
h1{{font-family:Fraunces,'Source Serif 4',Georgia,serif;font-size:clamp(24px,3.2vw,36px);line-height:1.15;margin:0 0 14px;
  font-weight:600;letter-spacing:-0.015em;color:#F6F1E8}}
p{{font-size:clamp(14px,1.4vw,16px);color:#E7DFD1;margin:0;line-height:1.55;max-width:50ch}}
.fallback{{position:absolute;right:7%;top:50%;width:180px;height:180px;transform:translateY(-50%);border-radius:50%;
  background:conic-gradient(from 200deg,rgba(255,255,255,.04),rgba(232,163,61,.55),rgba(246,241,232,.55),rgba(255,255,255,.04));
  -webkit-mask:radial-gradient(circle,transparent 52%,#000 53%,#000 70%,transparent 71%);
  mask:radial-gradient(circle,transparent 52%,#000 53%,#000 70%,transparent 71%);opacity:.8;filter:blur(.3px)}}
@media (max-width:640px){{.copy{{padding:26px 22px}}.fallback{{width:120px;height:120px;right:-30px;top:auto;bottom:-30px;transform:none;opacity:.45}}
  .scrim{{background:linear-gradient(180deg,rgba(14,12,48,.35),rgba(14,12,48,.1))}}}}"""
    body = (f'<div class="hero" id="root"><div id="stage" aria-hidden="true"></div><div class="fallback" aria-hidden="true"></div>'
            f'<div class="scrim"></div><div class="copy" id="copy"><h1>{html.escape(C.HERO_TITLE)}</h1>'
            f'<p>{html.escape(sub or C.HERO_SUB)}</p></div></div>')
    script = r"""
let mx = 0, my = 0;
const track = (e, frameEl) => { const w = (frameEl ? window.parent : window); const W = w.innerWidth, H = w.innerHeight;
  mx = (e.clientX / W - 0.5) * 2; my = (e.clientY / H - 0.5) * 2; };
try { on(window.parent.document, 'pointermove', e => track(e, true), {passive: true}); } catch (e) {}
on(window, 'pointermove', e => track(e, false), {passive: true});
const copy = document.getElementById('copy');
boot((THREE, renderer) => {
  const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
  cam.position.set(0, 0, 9);
  scene.fog = new THREE.Fog(0x161e2d, 7, 19);
  scene.environment = studioEnv(THREE, renderer, 0x2a3550);
  const narrow = () => stage.clientWidth < 640;
  const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(1.0, 0.33, 220, 28),
    new THREE.MeshPhysicalMaterial({color: 0xf3e6cf, metalness: 0.15, roughness: 0.18, clearcoat: 1, clearcoatRoughness: 0.08,
      sheen: 0.4, sheenColor: new THREE.Color(0xe8a33d), transparent: true, opacity: 0.94, envMapIntensity: 1.1}));
  scene.add(knot);
  scene.add(new THREE.AmbientLight(0xffffff, 0.35));
  const key = new THREE.DirectionalLight(0xffffff, 1.6); key.position.set(3, 4, 6); scene.add(key);
  const rim = new THREE.PointLight(0xe8a33d, 16, 20); rim.position.set(-2, -2, 3); scene.add(rim);
  const pink = new THREE.PointLight(0x8db3ec, 10, 20); pink.position.set(5, 3, -1); scene.add(pink);
  const N = narrow() ? 30 : 60, pos = new Float32Array(N * 3);
  for (let i = 0; i < N; i++) { pos[i * 3] = (Math.random() - 0.5) * 16; pos[i * 3 + 1] = (Math.random() - 0.5) * 6.5;
    pos[i * 3 + 2] = -7 + Math.random() * 9; }
  const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const dotc = document.createElement('canvas'); dotc.width = dotc.height = 32; const g = dotc.getContext('2d');
  const rg = g.createRadialGradient(16, 16, 0, 16, 16, 16); rg.addColorStop(0, 'rgba(255,255,255,1)'); rg.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = rg; g.fillRect(0, 0, 32, 32);
  const dots = new THREE.Points(pg, new THREE.PointsMaterial({size: 0.09, map: new THREE.CanvasTexture(dotc), transparent: true,
    opacity: 0.45, depthWrite: false, blending: THREE.AdditiveBlending, color: 0xf6f1e8}));
  scene.add(dots);
  const grid = new THREE.GridHelper(44, 44, 0xffffff, 0xffffff); grid.material.transparent = true; grid.material.opacity = 0.10; grid.visible = false;  // no grid floor in v3
  grid.position.y = -2.7; scene.add(grid);
  let px = 0, py = 0;
  return {
    resize(w, h) { cam.aspect = w / h; cam.updateProjectionMatrix();
      const n = w < 640; knot.visible = !n;
      const half = Math.tan(THREE.MathUtils.degToRad(17.5)) * 9 * cam.aspect;
      knot.position.set(Math.min(half * 0.55, 3.6), 0.05, 0); knot.scale.setScalar(Math.min(1.3, half / 7)); },
    frame(dt, t, still) {
      if (!still) { knot.rotation.x += dt * 0.06; knot.rotation.y += dt * 0.09; dots.rotation.y += dt * 0.006;
        knot.position.y = 0.05 + Math.sin(t * 0.6) * 0.08; px += (mx - px) * 0.05; py += (my - py) * 0.05; }
      cam.position.x = px * 0.35; cam.position.y = -py * 0.22; cam.lookAt(0, 0, 0);
      if (copy) copy.style.transform = `translate3d(${(-px * 6).toFixed(1)}px, ${(-py * 4).toFixed(1)}px, 0)`;
      renderer.render(scene, cam); },
    dispose() { disposeAll(scene); if (scene.environment) scene.environment.dispose(); }
  };
});
"""
    return _doc({"id": "hero", "use3d": bool(use_3d), "three": THREE_URL, "palette": p}, css, body, script)


# ------------------------------------------------------------------------------------------------ 2. money flow
def money_flow_html(items: list[dict], use_3d: bool = True, palette: dict | None = None) -> str:
    """3D columns of the year-end running balance per outlook (values from logic.year_end_balances)."""
    p = palette or T.scene_palette("light")
    pos_max = max([it["value"] for it in items] + [0.0])
    neg_max = -min([it["value"] for it in items] + [0.0])
    up = pos_max / (pos_max + neg_max) if (pos_max + neg_max) else 0.5
    up = min(max(up, 0.12), 0.88)  # keep room for the amount on both sides of the floor
    cols = []
    for it in items:
        c, text = p["outlook"].get(it["key"], p["accent"]), html.escape(it["text"])
        if it["value"] >= 0:
            bar = f'<i style="height:{it["value"] / (pos_max or 1) * 100:.1f}%;background:{c}"></i>'
            upper, lower = f"<span>{text}</span>{bar}", ""
        else:
            bar = f'<i style="height:{-it["value"] / (neg_max or 1) * 100:.1f}%;background:{c}"></i>'
            upper, lower = "", f"{bar}<span>{text}</span>"
        cols.append(f'<div class="fcol"><div class="fup">{upper}</div><div class="fdown">{lower}</div>'
                    f'<div class="fname">{html.escape(it["label"])}</div></div>')
    css = f"""
#root{{position:relative;height:370px;border-radius:14px;overflow:hidden;
  background:linear-gradient(180deg,{p['surface']},{p['surface']});border:1px solid {p['border']}}}
.head{{position:absolute;left:18px;top:14px;right:18px;z-index:3;pointer-events:none}}
.head b{{display:block;font:700 16px 'Plus Jakarta Sans',Inter,sans-serif;letter-spacing:-.01em}}
.head small{{display:block;font-size:12.5px;color:{p['muted']};margin-top:3px}}
#stage{{top:56px;cursor:grab;touch-action:pan-y}}#stage:active{{cursor:grabbing}}
.lbl{{position:absolute;z-index:2;transform:translate(-50%,-50%);font:600 13px Inter,sans-serif;white-space:nowrap;
  padding:3px 8px;border-radius:8px;background:{p['surface']};border:1px solid {p['border']};pointer-events:none;
  font-variant-numeric:tabular-nums;box-shadow:0 4px 12px rgba(0,0,0,.08)}}
.lbl em{{font-style:normal;font-weight:500;color:{p['muted']};margin-right:6px}}
.floor{{position:absolute;z-index:2;font-size:11.5px;color:{p['muted']};pointer-events:none;transform:translateY(-120%)}}
.tip{{position:absolute;z-index:4;pointer-events:none;max-width:260px;padding:10px 12px;border-radius:10px;font-size:13px;
  line-height:1.4;background:{p['surface']};border:1px solid {p['border']};box-shadow:0 12px 28px rgba(0,0,0,.18);
  opacity:0;transition:opacity .15s;backdrop-filter:blur(12px)}}
.tip b{{display:block;margin-bottom:2px}}
.fallback{{position:absolute;left:18px;right:18px;top:70px;bottom:16px;display:flex;gap:18px;align-items:stretch}}
.fcol{{flex:1;display:flex;flex-direction:column;min-width:0}}
.fup{{flex:{up:.3f};display:flex;flex-direction:column;justify-content:flex-end;align-items:center;border-bottom:1px dashed {p['border']}}}
.fdown{{flex:{1 - up:.3f};display:flex;flex-direction:column;justify-content:flex-start;align-items:center}}
.fcol i{{display:block;width:min(70%,90px);border-radius:6px;min-height:3px;opacity:.9}}
.fup i{{max-height:100%}}.fdown i{{max-height:100%}}
.fcol span{{font:600 13px Inter,sans-serif;margin:4px 0;font-variant-numeric:tabular-nums}}
.fname{{text-align:center;font-size:12.5px;color:{p['muted']};padding-top:4px}}"""
    sr = "".join(f"<li>{html.escape(it['label'])}: {html.escape(it['text'])}</li>" for it in items)
    body = (f'<div id="root" role="figure" aria-label="{html.escape(C.FLOW_TITLE)}"><div class="head"><b>{html.escape(C.FLOW_TITLE)}</b>'
            f'<small>{html.escape(C.FLOW_HINT)}</small></div><div id="stage"></div><div class="tip" id="tip"></div>'
            f'<div class="fallback" aria-hidden="true">{"".join(cols)}</div><ul class="sr">{sr}</ul></div>')
    script = r"""
const items = CFG.items, tip = document.getElementById('tip');
boot((THREE, renderer) => {
  const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
  const top = Math.max(...items.map(d => Math.abs(d.value)), 1), H = 3.0;
  const up = Math.max(...items.map(d => d.value), 0) / top * H, down = Math.max(...items.map(d => -d.value), 0) / top * H;
  const midY = (up - down) / 2;
  scene.add(new THREE.HemisphereLight(0xffffff, P.mode === 'dark' ? 0x222244 : 0xdde3f5, 1.4));
  const sun = new THREE.DirectionalLight(0xffffff, 1.8); sun.position.set(4, 6, 6); scene.add(sun);
  const g = new THREE.Group(); scene.add(g);
  const floorMat = new THREE.MeshBasicMaterial({color: P.accent, transparent: true, opacity: P.mode === 'dark' ? 0.16 : 0.10,
    side: THREE.DoubleSide, depthWrite: false});
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(8.4, 3.0), floorMat); floor.rotation.x = -Math.PI / 2; g.add(floor);
  const edge = new THREE.LineSegments(new THREE.EdgesGeometry(floor.geometry),
    new THREE.LineBasicMaterial({color: P.accent, transparent: true, opacity: 0.45})); edge.rotation.x = -Math.PI / 2; g.add(edge);
  const cols = items.map((d, i) => {
    const color = new THREE.Color(P.outlook[d.key] || P.accent);
    const m = new THREE.Mesh(new THREE.BoxGeometry(1.15, 1, 1.15), new THREE.MeshStandardMaterial({color, roughness: 0.35,
      metalness: 0.08, transparent: true, opacity: 0.94, emissive: color, emissiveIntensity: 0.08}));
    m.position.x = (i - (items.length - 1) / 2) * 2.5; m.userData = d; g.add(m);
    const lbl = document.createElement('div'); lbl.className = 'lbl';
    lbl.innerHTML = `<em></em>${d.text}`; lbl.querySelector('em').textContent = d.short; root.appendChild(lbl);
    return {m, d, h: Math.max(Math.abs(d.value) / top * H, 0.04), s: Math.sign(d.value) || 1, lbl};
  });
  const floorLbl = document.createElement('div'); floorLbl.className = 'floor'; floorLbl.textContent = CFG.floor; root.appendChild(floorLbl);
  let yaw = -0.3, vel = 0, drag = null, grown = -1, hover = null, w = 1, h = 1;
  const ray = new THREE.Raycaster(), ptr = new THREE.Vector2(), v = new THREE.Vector3();
  const cvs = renderer.domElement;
  on(cvs, 'pointerdown', e => { drag = {x: e.clientX, yaw}; cvs.setPointerCapture(e.pointerId); });
  on(cvs, 'pointerup', e => { drag = null; });
  on(cvs, 'pointerleave', () => { hover = null; tip.style.opacity = 0; });
  on(cvs, 'pointermove', e => {
    const r = cvs.getBoundingClientRect();
    if (drag) { const ny = drag.yaw + (e.clientX - drag.x) * 0.008; vel = ny - yaw; yaw = Math.max(-1.3, Math.min(1.3, ny)); }
    ptr.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1);
    ray.setFromCamera(ptr, cam);
    const hit = ray.intersectObjects(cols.map(c => c.m))[0];
    hover = hit ? hit.object : null;
    if (hover) { const d = hover.userData;
      tip.innerHTML = `<b></b><span></span>`; tip.querySelector('b').textContent = `${d.label}: ${d.text}`;
      tip.querySelector('span').textContent = d.value >= 0 ? CFG.good : CFG.bad;
      const tx = Math.min(e.clientX - r.left + 14, r.width - 270), ty = e.clientY - r.top + 70;
      tip.style.left = Math.max(tx, 8) + 'px'; tip.style.top = ty + 'px'; tip.style.opacity = 1; }
    else tip.style.opacity = 0;
  });
  return {
    resize(W, Hh) { w = W; h = Hh; cam.aspect = W / Hh;
      const fitW = 5.2 / (Math.tan(THREE.MathUtils.degToRad(15)) * cam.aspect), fitH = 3.9 / Math.tan(THREE.MathUtils.degToRad(15));
      const far = Math.max(fitW, fitH * 0.62, 8.5);
      cam.position.set(0, midY + far * 0.42, far); cam.lookAt(0, midY - 0.1, 0); cam.updateProjectionMatrix(); },
    frame(dt, t, still) {
      if (grown < 0 && !still) grown = t;
      const p = grown < 0 ? 1 : ease((t - grown) / 1.3);
      if (!still) { if (!drag) { yaw += vel; vel *= 0.92; } g.rotation.y = yaw + (drag ? 0 : Math.sin(t * 0.25) * 0.12); }
      cols.forEach((c, i) => { const q = grown < 0 ? 1 : ease((t - grown - i * 0.12) / 1.2);
        c.m.scale.y = Math.max(c.h * q, 0.001); c.m.position.y = c.s * c.h * q / 2;
        c.m.material.emissiveIntensity = c.m === hover ? 0.32 : 0.08;
        v.set(c.m.position.x, c.s * (c.h * q + 0.28), 0).applyMatrix4(g.matrixWorld).project(cam);
        c.lbl.style.left = ((v.x + 1) / 2 * w) + 'px'; c.lbl.style.top = (56 + (1 - v.y) / 2 * h) + 'px'; });
      v.set(4.2, 0, 1.5).applyMatrix4(g.matrixWorld).project(cam);
      floorLbl.style.left = Math.min(w - 110, Math.max(8, (v.x + 1) / 2 * w - 40)) + 'px'; floorLbl.style.top = (56 + (1 - v.y) / 2 * h) + 'px';
      g.updateMatrixWorld(); renderer.render(scene, cam); },
    dispose() { disposeAll(scene); }
  };
});
"""
    data = [dict(it, short=C.OUTLOOK_SHORT.get(it["key"], it["label"])) for it in items]
    return _doc({"id": "flow", "use3d": bool(use_3d), "three": THREE_URL, "palette": p, "items": data,
                 "floor": C.FLOW_FLOOR, "good": C.FLOW_TIP_GOOD, "bad": C.FLOW_TIP_BAD}, css, body, script)


# ------------------------------------------------------------------------------------------------ 3. cost donut
def donut_html(slices: list[dict], use_3d: bool = True, palette: dict | None = None) -> str:
    """Tilted 3D donut of the cost split (values from logic.cost_slices); flat CSS donut as the fallback."""
    p = palette or T.scene_palette("light")
    stops, acc = [], 0.0
    for s in slices:
        c = p["line"].get(s["key"], p["accent"])
        stops.append(f"{c} {acc * 360:.2f}deg {(acc + s['share']) * 360:.2f}deg")
        acc += s["share"]
    legend = "".join(
        f'<li data-i="{n}"><i style="background:{p["line"].get(s["key"], p["accent"])}"></i><span class="nm">{html.escape(s["label"])}'
        f'<small>{html.escape(s["tag"])}</small></span><span class="am">{html.escape(s["text"])}<small>{html.escape(s["share_text"])}</small></span></li>'
        for n, s in enumerate(slices))
    css = f"""
#root{{position:relative;height:390px;border-radius:14px;overflow:hidden;display:grid;grid-template-columns:58% 42%;
  background:{p['surface']};border:1px solid {p['border']}}}
.head{{position:absolute;left:18px;top:14px;z-index:3;pointer-events:none}}
.head b{{display:block;font:700 16px 'Plus Jakarta Sans',Inter,sans-serif;letter-spacing:-.01em}}
.head small{{display:block;font-size:12.5px;color:{p['muted']};margin-top:3px}}
.left{{position:relative}}#stage{{top:40px}}
.fallback{{position:absolute;left:50%;top:55%;width:min(220px,70%);aspect-ratio:1;transform:translate(-50%,-50%);border-radius:50%;
  background:conic-gradient({",".join(stops)});-webkit-mask:radial-gradient(circle,transparent 56%,#000 57%);mask:radial-gradient(circle,transparent 56%,#000 57%)}}
ul{{list-style:none;margin:0;padding:64px 18px 16px 4px;display:flex;flex-direction:column;justify-content:center;gap:6px}}
li{{display:grid;grid-template-columns:12px 1fr auto;gap:10px;align-items:center;padding:8px 10px;border-radius:10px;
  transition:background .2s;cursor:default}}
li:hover,li.on{{background:{p['border']}}}
li i{{width:12px;height:12px;border-radius:4px}}
.nm{{font-size:13.5px;line-height:1.25}}.nm small,.am small{{display:block;font-size:11.5px;color:{p['muted']}}}
.am{{text-align:right;font:600 13.5px Inter,sans-serif;font-variant-numeric:tabular-nums}}
.tip{{position:absolute;z-index:4;pointer-events:none;padding:9px 12px;border-radius:10px;font-size:13px;line-height:1.4;
  background:{p['surface']};border:1px solid {p['border']};box-shadow:0 12px 28px rgba(0,0,0,.18);opacity:0;transition:opacity .15s;
  max-width:240px}}
.tip b{{display:block}}
@media (max-width:560px){{#root{{grid-template-columns:1fr;grid-template-rows:205px 1fr}}ul{{padding:0 12px 10px;gap:2px}}
  li{{padding:5px 8px}}#stage{{top:44px}}.fallback{{top:60%;width:140px}}}}"""
    body = (f'<div id="root" role="figure" aria-label="{html.escape(C.DONUT_TITLE)}"><div class="head"><b>{html.escape(C.DONUT_TITLE)}</b>'
            f'<small>{html.escape(C.DONUT_HINT)}</small></div><div class="left"><div id="stage"></div>'
            f'<div class="fallback" aria-hidden="true"></div><div class="tip" id="tip"></div></div><ul>{legend}</ul></div>')
    script = r"""
const sl = CFG.slices, tip = document.getElementById('tip'), lis = [...document.querySelectorAll('li')];
let hoverI = -1;
lis.forEach((li, i) => { on(li, 'pointerenter', () => { hoverI = i; }); on(li, 'pointerleave', () => { hoverI = -1; }); });
boot((THREE, renderer) => {
  const scene = new THREE.Scene(), cam = new THREE.PerspectiveCamera(32, 1, 0.1, 100); cam.position.set(0, 0, 9);
  scene.environment = studioEnv(THREE, renderer, P.mode === 'dark' ? 0x20234a : 0xdfe4f7);
  scene.add(new THREE.AmbientLight(0xffffff, 0.5));
  const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(2, 5, 6); scene.add(sun);
  const g = new THREE.Group(); g.rotation.x = -0.82; scene.add(g);
  const R = 2.05, r = 1.2; let a = Math.PI / 2;
  const parts = sl.map((s, i) => {
    const span = s.share * Math.PI * 2, pad = span > 0.06 ? 0.012 : 0;
    const a0 = a - pad, a1 = a - span + pad; a -= span;
    const sh = new THREE.Shape(); sh.moveTo(Math.cos(a0) * R, Math.sin(a0) * R); sh.absarc(0, 0, R, a0, a1, true);
    sh.lineTo(Math.cos(a1) * r, Math.sin(a1) * r); sh.absarc(0, 0, r, a1, a0, false);
    const geo = new THREE.ExtrudeGeometry(sh, {depth: 0.5, bevelEnabled: true, bevelThickness: 0.04, bevelSize: 0.03,
      bevelSegments: 2, curveSegments: Math.max(4, Math.ceil(72 * s.share))});
    const m = new THREE.Mesh(geo, new THREE.MeshPhysicalMaterial({color: new THREE.Color(P.line[s.key] || P.accent),
      roughness: 0.32, metalness: 0.05, clearcoat: 0.7, clearcoatRoughness: 0.2, envMapIntensity: 0.9}));
    const mid = (a0 + a1) / 2; m.userData = {i, dir: new THREE.Vector3(Math.cos(mid), Math.sin(mid), 0), lift: 0};
    g.add(m); return m;
  });
  const ray = new THREE.Raycaster(), ptr = new THREE.Vector2(); const cvs = renderer.domElement; let sceneHover = -1;
  on(cvs, 'pointermove', e => { const rc = cvs.getBoundingClientRect();
    ptr.set((e.clientX - rc.left) / rc.width * 2 - 1, -(e.clientY - rc.top) / rc.height * 2 + 1); ray.setFromCamera(ptr, cam);
    const hit = ray.intersectObjects(parts)[0]; sceneHover = hit ? hit.object.userData.i : -1;
    if (sceneHover >= 0) { const s = sl[sceneHover]; tip.innerHTML = '<b></b><span></span>';
      tip.querySelector('b').textContent = `${s.label} (${s.tag})`; tip.querySelector('span').textContent = s.tip;
      tip.style.left = Math.min(e.clientX - rc.left + 12, rc.width - 200) + 'px'; tip.style.top = (e.clientY - rc.top + 40) + 'px';
      tip.style.opacity = 1; } else tip.style.opacity = 0; });
  on(cvs, 'pointerleave', () => { sceneHover = -1; tip.style.opacity = 0; });
  return {
    resize(w, h) { cam.aspect = w / h; cam.position.z = w < 330 ? 11 : 9; cam.updateProjectionMatrix(); },
    frame(dt, t, still) {
      const hi = sceneHover >= 0 ? sceneHover : hoverI;
      lis.forEach((li, i) => li.classList.toggle('on', i === hi));
      if (!still) g.rotation.z = Math.sin(t * 0.2) * 0.18;
      parts.forEach(m => { const u = m.userData, target = u.i === hi ? 1 : 0;
        u.lift += (target - u.lift) * (still ? 1 : Math.min(dt * 10, 1));
        m.position.copy(u.dir).multiplyScalar(u.lift * 0.22); m.position.z = u.lift * 0.22; });
      renderer.render(scene, cam); },
    dispose() { disposeAll(scene); if (scene.environment) scene.environment.dispose(); }
  };
});
"""
    data = [dict(s, tip=C.SLICE_TIP.format(amount=s["text"], share=s["share_text"])) for s in slices]
    return _doc({"id": "donut", "use3d": bool(use_3d), "three": THREE_URL, "palette": p, "slices": data}, css, body, script)
