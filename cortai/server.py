"""Painel web local (stdlib only). `python cortai.py serve` e abre o navegador."""

from __future__ import annotations

import json
import re
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from pipeline.util import log

from .dashboard import snapshot
from .db import DB

PAGE = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>cortai — cortes</title>
<style>
:root{--bg:#0b0c0f;--card:#14161b;--line:#23262e;--fg:#e8eaed;--dim:#8b929e;--acc:#ffd400;--ok:#3ddc84;--bad:#ff5c5c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 ui-sans-serif,system-ui,Segoe UI,Roboto,sans-serif}
header{position:sticky;top:0;z-index:5;display:flex;align-items:center;gap:16px;padding:14px 20px;background:rgba(11,12,15,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
header h1{margin:0;font-size:15px;font-weight:600;letter-spacing:.02em}
header h1 b{color:var(--acc)}
.pill{font-size:11px;padding:3px 9px;border-radius:99px;border:1px solid var(--line);color:var(--dim)}
.pill.live{color:var(--ok);border-color:rgba(61,220,132,.4)}
main{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:18px;padding:18px 20px 60px;align-items:start}
@media(max-width:1000px){main{grid-template-columns:1fr}}
h2{font-size:11px;text-transform:uppercase;letter-spacing:.12em;color:var(--dim);margin:0 0 10px;font-weight:600}
.streams{display:grid;gap:10px;margin-bottom:22px}
.addlive{display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap}
.addlive input{flex:1 1 220px;min-width:0;padding:9px 12px;border-radius:9px;border:1px solid var(--line);background:#0f1116;color:var(--fg);font-size:13px}
.addlive input:focus{outline:none;border-color:#3a3f4b}
.addlive button{padding:9px 16px;border-radius:9px;border:1px solid #2f3540;background:#1b1e25;color:var(--fg);font-weight:600;cursor:pointer}
.addlive button:hover{border-color:#4a515f}
.stream .kill{margin-left:auto;background:none;border:1px solid var(--line);color:var(--dim);border-radius:7px;padding:4px 9px;cursor:pointer;font-size:12px}
.stream .kill:hover{border-color:rgba(255,92,92,.5);color:var(--bad)}
.stream{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px;display:flex;gap:12px;align-items:center}
.pv{width:184px;aspect-ratio:16/9;border-radius:8px;background:#000;object-fit:cover;flex:0 0 auto;display:block}
.sinfo{flex:1 1 auto;min-width:0;display:grid;gap:7px}
.srow{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.stream .dot{width:8px;height:8px;border-radius:99px;background:var(--bad);flex:0 0 auto}
.stream .dot.on{background:var(--ok);box-shadow:0 0 0 4px rgba(61,220,132,.12)}
.stream .name{font-weight:600}
.stream .meta{color:var(--dim);font-size:12px;white-space:nowrap}
.bar{height:4px;background:#1d2027;border-radius:99px;overflow:hidden;flex:1 1 140px;min-width:100px}
.bar i{display:block;height:100%;background:var(--acc);transition:width .4s}
.clips{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:14px}
.clip{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;transition:border-color .15s}
.clip:hover{border-color:#3a3f4b}
.clip .thumbwrap{position:relative;aspect-ratio:9/16;background:#0f1116;cursor:pointer;overflow:hidden}
.clip img{width:100%;height:100%;object-fit:cover;display:block}
.clip .nocap{position:absolute;inset:0;display:grid;place-items:center;color:#3a3f4b;font-size:11px}
.clip .badges{position:absolute;top:8px;left:8px;right:8px;display:flex;gap:6px;justify-content:space-between}
.badge{font-size:10px;font-weight:700;padding:3px 7px;border-radius:6px;background:rgba(0,0,0,.7);letter-spacing:.04em}
.badge.score{color:var(--acc)}
.badge.layout{color:#9ad1ff}
.badge.size{color:var(--dim);font-weight:500}
.clip .body{padding:10px 12px 12px}
.clip .t{font-weight:600;font-size:13px;line-height:1.35;margin-bottom:4px}
.clip .h{font-size:11px;color:var(--acc);margin-bottom:6px}
.clip .c{font-size:11px;color:var(--dim);max-height:3.2em;overflow:hidden}
.clip .tags{font-size:10px;color:#5c93c4;margin-top:6px;word-break:break-word}
.clip .foot{display:flex;justify-content:space-between;margin-top:8px;font-size:10px;color:#555c69}
.clip .vote{display:flex;gap:6px;margin-top:8px}
.clip .vote button{flex:1;background:#1b1e25;border:1px solid var(--line);color:var(--dim);border-radius:7px;padding:5px 0;cursor:pointer;font-size:13px;transition:.15s}
.clip .vote button:hover{border-color:#3a3f4b;color:var(--fg)}
.clip .vote .up.on{background:rgba(61,220,132,.16);border-color:rgba(61,220,132,.5);color:var(--ok)}
.clip .vote .dn.on{background:rgba(255,92,92,.16);border-color:rgba(255,92,92,.5);color:var(--bad)}
.clip .pub{display:block;width:100%;margin-top:6px;padding:6px 0;border-radius:7px;border:1px solid #2f3540;background:#1b1e25;color:var(--dim);font-size:11px;text-align:center;text-decoration:none;cursor:pointer}
.clip .pub:hover{border-color:#4a515f;color:var(--fg)}
.clip .pub.done{color:var(--ok);border-color:rgba(61,220,132,.4)}
.clip .pub.up{color:var(--acc);border-color:rgba(255,212,0,.4)}
.clip .pub.err{color:var(--bad);border-color:rgba(255,92,92,.4)}
.side{display:grid;gap:18px;position:sticky;top:70px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.panel .ph{padding:10px 12px;border-bottom:1px solid var(--line);font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--dim)}
.log{max-height:340px;overflow:auto;padding:8px 10px;font:11px/1.6 ui-monospace,Consolas,monospace}
.log div{display:flex;gap:8px;white-space:pre-wrap;word-break:break-word}
.log time{color:#4d5460;flex:0 0 auto}
.log .err{color:var(--bad)}
.log .warn{color:var(--acc)}
.log .score{color:var(--ok)}
.empty{padding:24px;text-align:center;color:#4d5460;font-size:12px}
dialog{border:none;background:transparent;padding:0;max-width:min(92vw,420px)}
dialog::backdrop{background:rgba(0,0,0,.8)}
dialog video{width:100%;border-radius:12px;display:block}
dialog button{position:absolute;top:-34px;right:0;background:none;border:none;color:#fff;font-size:22px;cursor:pointer}
</style></head>
<body>
<header>
  <h1>cortai <b>·</b> cortes</h1>
  <span class="pill" id="live-pill">—</span>
  <span class="pill" id="clip-pill">—</span>
  <span class="pill" id="cost-pill">—</span>
  <span class="pill" id="fb-pill">—</span>
  <span class="pill" id="clock">—</span>
</header>
<main>
  <div>
    <h2>lives</h2>
    <form class="addlive" id="addform">
      <input id="newurl" placeholder="https://www.twitch.tv/canal" required>
      <input id="newtitle" placeholder="título (opcional)">
      <button type="submit">adicionar</button>
    </form>
    <div class="streams" id="streams"></div>
    <h2>clipes</h2>
    <div class="clips" id="clips"></div>
  </div>
  <div class="side">
    <div class="panel"><div class="ph">candidatos</div><div class="log" id="cands"></div></div>
    <div class="panel"><div class="ph">eventos</div><div class="log" id="logs"></div></div>
  </div>
</main>
<dialog id="player"><button onclick="closePlayer()">×</button><video id="v" controls playsinline></video></dialog>
<script>
let lastJson='';
const cards=new Map();
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}

function buildCard(){
  const root=document.createElement('div');root.className='stream';
  const vid=document.createElement('video');
  vid.className='pv';vid.muted=true;vid.autoplay=true;vid.playsInline=true;vid.loop=true;
  const info=document.createElement('div');info.className='sinfo';
  const row1=document.createElement('div');row1.className='srow';
  const dot=document.createElement('span');dot.className='dot';
  const name=document.createElement('span');name.className='name';
  const meta=document.createElement('span');meta.className='meta';
  row1.append(dot,name,meta);
  const row2=document.createElement('div');row2.className='srow';
  const bar=document.createElement('span');bar.className='bar';
  const fill=document.createElement('i');bar.append(fill);
  const mBuf=document.createElement('span');mBuf.className='meta';
  const mFace=document.createElement('span');mFace.className='meta';
  const mClips=document.createElement('span');mClips.className='meta';
  const kill=document.createElement('button');kill.className='kill';kill.textContent='parar';
  row2.append(bar,mBuf,mFace,mClips,kill);
  info.append(row1,row2);root.append(vid,info);
  return {root,vid,dot,name,meta,fill,mBuf,mFace,mClips,kill,previewAt:null};
}

function renderStreams(list){
  const host=document.getElementById('streams');
  if(!list.length){host.innerHTML='<div class="empty">nenhuma live cadastrada</div>';cards.clear();return}
  const seen=new Set();
  for(const s of list){
    seen.add(s.slug);
    let c=cards.get(s.slug);
    if(!c){c=buildCard();cards.set(s.slug,c);host.appendChild(c.root)}
    c.dot.className='dot'+(s.live?' on':'');
    c.name.textContent=s.slug;
    c.meta.textContent=s.platform+' · '+(s.title||'—');
    c.fill.style.width=s.buffer_pct+'%';
    c.mBuf.textContent=s.buffer_s+'s buffer';
    c.mFace.textContent=s.facecam?('facecam '+(s.facecam.w|0)+'px'):'sem facecam';
    c.mClips.textContent=s.clips+' clipes';
    c.kill.onclick=()=>stopStream(s.slug);
    c.kill.style.display = s.status==='active' ? 'block' : 'none';
    if(s.preview_at && c.previewAt!==s.preview_at){
      c.previewAt=s.preview_at;
      c.vid.src=s.preview_url+'?t='+s.preview_at;
      const p=c.vid.play();if(p&&p.catch)p.catch(()=>{});
    }
  }
  for(const [slug,c] of cards){if(!seen.has(slug)){c.root.remove();cards.delete(slug)}}
}

function render(d){
  window.CAN_PUBLISH = !!(d.publish && d.publish.ready);
  const ap=d.auto_publish||{};
  if(ap.enabled){
    document.getElementById('clip-pill').title = 'publica sozinho a partir de nota '+ap.min_score+' ('+ap.privacy+')';
    document.getElementById('clip-pill').textContent += ' · auto ≥'+ap.min_score;
  }
  const live=d.streams.filter(s=>s.live).length;
  document.getElementById('live-pill').textContent=live+'/'+d.streams.length+' no ar';
  document.getElementById('live-pill').className='pill'+(live?' live':'');
  document.getElementById('clip-pill').textContent=d.totals.clips+' clipes'+(d.published_today?(' · '+d.published_today+' no YT hoje'):'');
  const fb=d.feedback||{};
  document.getElementById('fb-pill').textContent = fb.rated
    ? ('precisão '+Math.round(fb.precision*100)+'% · '+fb.good+'👍 '+fb.bad+'👎')
    : 'sem avaliação';
  document.getElementById('fb-pill').className='pill'+(fb.rated && fb.precision>=0.7?' live':'');
  const c=d.cost||{};
  const hoje=c.hoje||{};
  const cp=document.getElementById('cost-pill');
  cp.textContent='US$ '+(hoje.usd||0).toFixed(2)+' · R$ '+(hoje.brl||0).toFixed(2)+' hoje';
  cp.title='total: US$ '+(c.total&&c.total.usd||0).toFixed(2)
    +' | ASR US$ '+(hoje.by_kind&&hoje.by_kind.asr||0).toFixed(2)
    +' | LLM US$ '+(hoje.by_kind&&hoje.by_kind.llm||0).toFixed(2)
    +' | '+(hoje.calls||0)+' chamadas'
    +' | US$ '+(hoje.per_clip_usd||0).toFixed(3)+' por clipe';
  document.getElementById('clock').textContent=new Date().toLocaleTimeString('pt-BR');

  renderStreams(d.streams);

  document.getElementById('clips').innerHTML = d.clips.length? d.clips.map(c=>{
    const thumb=c.has_thumb? '<img loading="lazy" src="'+c.thumb_url+'?t='+c.id+'" alt="">':'<div class="nocap">sem preview</div>';
    const click=c.video_url? 'onclick="play(\''+c.video_url+'\')"':'';
    return '<div class="clip"><div class="thumbwrap" '+click+'>'+thumb+
      '<div class="badges"><span class="badge score">'+c.score+'</span>'+
      '<span class="badge layout">'+esc(c.layout)+'</span>'+
      '<span class="badge size">'+c.size_mb+'MB</span></div></div>'+
      '<div class="body"><div class="t">'+esc(c.title||'—')+'</div>'+
      '<div class="h">'+esc(c.hook||'')+'</div>'+
      '<div class="c">'+esc(c.caption||'')+'</div>'+
      '<div class="tags">'+esc(c.hashtags||'')+'</div>'+
      '<div class="foot"><span>'+esc(c.when)+'</span><span>#'+c.id+'</span></div>'+
      '<div class="vote">'+
        '<button class="up'+(c.feedback===1?' on':'')+'" onclick="vote('+c.id+',1)" title="publicaria">👍</button>'+
        '<button class="dn'+(c.feedback===-1?' on':'')+'" onclick="vote('+c.id+',-1)" title="nao presta">👎</button>'+
      '</div>'+publishControl(c)+'</div></div>';
  }).join('') : '<div class="empty">nenhum clipe ainda. o sistema espera o buffer encher e um pico de energia.</div>';

  document.getElementById('cands').innerHTML = d.candidates.length? d.candidates.map(c=>{
    const m=c.msg||''; const sc=(m.match(/score=([\d.]+)/)||[])[1];
    const keep=/keep=True/.test(m);
    return '<div><time>'+c.time+'</time><span class="'+(keep?'score':'')+'">'+esc(c.slug)+' '+esc(m.replace('candidato ',''))+'</span></div>';
  }).join('') : '<div class="empty">—</div>';

  document.getElementById('logs').innerHTML = d.logs.length? d.logs.map(l=>{
    const cls=l.level==='error'?'err':(l.level==='warn'?'warn':'');
    return '<div><time>'+l.time+'</time><span class="'+cls+'">'+esc(l.slug||'')+' '+esc(l.msg)+'</span></div>';
  }).join('') : '<div class="empty">—</div>';
}
async function tick(){
  try{
    const r=await fetch('/api/state',{cache:'no-store'});
    const t=await r.text();
    if(t!==lastJson){lastJson=t;render(JSON.parse(t));}
    document.getElementById('clock').textContent=new Date().toLocaleTimeString('pt-BR');
  }catch(e){document.getElementById('live-pill').textContent='servidor fora';}
}
async function vote(id, v){
  try{
    const r = await fetch('/api/clip/'+id+'/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({vote:v})});
    if(!r.ok) return;
    lastJson='';
    tick();
  }catch(e){}
}
function publishControl(c){
  const p = c.published || {};
  if(p.state==='done') return '<a class="pub done" href="'+esc(p.url||'#')+'" target="_blank" rel="noopener">no YouTube ✓</a>';
  if(p.state==='uploading'){ const pct = p.progress? Math.round(p.progress*100):0; return '<span class="pub up">enviando '+pct+'%</span>'; }
  if(p.state==='error') return '<button class="pub err" onclick="publishClip('+c.id+')" title="'+esc(p.error||'')+'">reenviar</button>';
  if(!window.CAN_PUBLISH) return '';
  return '<button class="pub" onclick="publishClip('+c.id+')">publicar no YouTube</button>';
}
async function publishClip(id){
  const r = await fetch('/api/clip/'+id+'/publish',{method:'POST'});
  const j = await r.json().catch(()=>({}));
  if(j.error) alert(j.error);
  lastJson=''; tick();
}
async function stopStream(slug){
  if(!confirm('parar '+slug+'?')) return;
  await fetch('/api/streams/'+encodeURIComponent(slug)+'/stop',{method:'POST'});
  lastJson='';tick();
}
document.getElementById('addform').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const url=document.getElementById('newurl'), title=document.getElementById('newtitle');
  const r = await fetch('/api/streams',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({url:url.value.trim(), title:title.value.trim()})});
  const j = await r.json().catch(()=>({}));
  if(!j.ok){ alert('erro: '+(j.error||r.status)); return; }
  url.value=''; title.value='';
  lastJson=''; tick();
});
function play(url){document.getElementById('v').src=url;document.getElementById('player').showModal()}
function closePlayer(){const v=document.getElementById('v');v.pause();v.src='';document.getElementById('player').close()}
tick();setInterval(tick,3000);
</script></body></html>"""


LOGIN_PAGE = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>cortai — entrar</title>
<style>
:root{--bg:#0b0c0f;--card:#14161b;--line:#23262e;--fg:#e8eaed;--dim:#8b929e;--acc:#ffd400;--bad:#ff5c5c}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--fg);
font:14px/1.5 ui-sans-serif,system-ui,Segoe UI,Roboto,sans-serif}
form{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:28px;width:min(92vw,340px)}
h1{margin:0 0 4px;font-size:16px;font-weight:600}
h1 b{color:var(--acc)}
p{margin:0 0 18px;color:var(--dim);font-size:12px}
input{width:100%;padding:11px 13px;border-radius:9px;border:1px solid var(--line);background:#0f1116;color:var(--fg);font-size:14px}
input:focus{outline:none;border-color:#3a3f4b}
button{margin-top:12px;width:100%;padding:11px;border-radius:9px;border:1px solid #2f3540;background:#1b1e25;color:var(--fg);font-weight:600;cursor:pointer}
button:hover{border-color:#4a515f}
.err{margin-top:12px;color:var(--bad);font-size:12px}
</style></head><body>
<form method="post" action="/login">
  <h1>cortai <b>·</b> cortes</h1>
  <p>painel privado</p>
  <input type="password" name="password" placeholder="senha" autofocus autocomplete="current-password">
  <button type="submit">entrar</button>
  {erro}
</form></body></html>"""


def _deep_merge(base: dict, override: dict) -> dict:
    import copy

    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


LIMITS: dict[str, tuple[float, float]] = {
    "live.window_s": (30, 180),
    "live.cycle_s": (5, 60),
    "live.buffer_seconds": (120, 1800),
    "live.min_buffer_s": (20, 300),
    "moments.peak_z": (0.3, 4.0),
    "moments.min_sep_s": (5, 300),
    "moments.context_pre_s": (2, 60),
    "moments.context_post_s": (5, 90),
    "moments.min_clip_s": (5, 60),
    "moments.max_clip_s": (10, 90),
    "classify.min_score": (0, 10),
    "classify.frames": (1, 10),
    "render.fps": (15, 60),
    "render.crf": (14, 32),
    "render.karaoke_size": (40, 140),
    "render.karaoke_words": (1, 6),
    "render.karaoke_margin_v": (40, 700),
    "render.hook_size": (40, 160),
    "render.blur_sigma": (0, 60),
    "render.pip_scale": (0.15, 0.6),
    "render.pip_offset_y": (0, 1200),
    "branding.logo_width": (60, 600),
    "publish.auto_min_score": (0, 10),
    "maintenance.clip_retention_days": (1, 3650),
    "maintenance.keep_unpublished_days": (0, 3650),
    "maintenance.db_retention_days": (7, 3650),
    "maintenance.run_every_hours": (1, 168),
}


def _sanitize_config(data: dict) -> dict:
    """Evita config que quebra o pipeline (numero fora de faixa, enum invalido)."""
    for path, (lo, hi) in LIMITS.items():
        keys = path.split(".")
        node = data
        for key in keys[:-1]:
            node = node.get(key) if isinstance(node, dict) else None
            if not isinstance(node, dict):
                break
        if isinstance(node, dict) and keys[-1] in node:
            try:
                value = float(node[keys[-1]])
                node[keys[-1]] = int(value) if float(value).is_integer() and lo >= 1 else value
                node[keys[-1]] = max(lo, min(hi, node[keys[-1]]))
            except (TypeError, ValueError):
                node[keys[-1]] = lo

    enums = {
        ("render", "mode"): {"pad_blur", "crop"},
        ("render", "pip_position"): {"tl", "tr", "bl", "br"},
        ("branding", "logo_position"): {"tl", "tr", "bl", "br"},
        ("publish", "privacy"): {"public", "unlisted", "private"},
        ("classify", "mode"): {"cascade", "llm", "jev"},
    }
    for (section, key), allowed in enums.items():
        node = data.get(section)
        if isinstance(node, dict) and key in node and node[key] not in allowed:
            node[key] = sorted(allowed)[0]
    return data


def _cookie(token: str, secure: bool, max_age: int) -> str:
    parts = [
        f"cortai_session={token}",
        "Path=/",
        "HttpOnly",
        "SameSite=Strict",
        f"Max-Age={max_age}",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def _handler(cfg: Any, db: DB, auth: Any = None, cookie_secure: bool = False):
    out_dir = cfg.out_dir.resolve()
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: Any) -> None:  # silencia o log de cada request
            return

        # -- helpers de sessao ------------------------------------------
        def _token(self) -> str | None:
            raw = self.headers.get("Cookie") or ""
            for part in raw.split(";"):
                name, _, value = part.strip().partition("=")
                if name == "cortai_session":
                    return value
            return None

        def _authed(self) -> bool:
            if auth is None or not auth.enabled:
                return True  # sem senha configurada: so roda em localhost
            return auth.validate(self._token())

        def _redirect(self, location: str, cookie: str | None = None) -> None:
            self.send_response(302)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()

        def _send(self, code: int, body: bytes, ctype: str, cache: bool = False) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store" if not cache else "public, max-age=3600")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            path = unquote(self.path.split("?")[0])

            if path == "/login":
                body = LOGIN_PAGE.replace("{erro}", "").encode("utf-8")
                self._send(200, body, "text/html; charset=utf-8")
                return

            if path == "/logout":
                self._redirect("/login", _cookie("", cookie_secure, 0))
                return

            if not self._authed():
                if path.startswith("/api/"):
                    self._send(401, b'{"error":"unauthorized"}', "application/json; charset=utf-8")
                    return
                self._redirect("/login")
                return

            if path in ("/", "/index.html"):
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
                return

            if path == "/settings":
                from .pages import SETTINGS_PAGE

                self._send(200, SETTINGS_PAGE.encode("utf-8"), "text/html; charset=utf-8")
                return

            if path == "/api/config":
                body = json.dumps(cfg.data, ensure_ascii=False, default=str).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8")
                return

            if path == "/api/state":
                body = json.dumps(snapshot(cfg, db), ensure_ascii=False).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8")
                return

            if path.startswith("/media/"):
                self._serve_media(path)
                return

            if path.startswith("/preview/"):
                self._serve_preview(path)
                return

            self._send(404, b"not found", "text/plain")

        def do_POST(self) -> None:  # noqa: N802
            path = unquote(self.path.split("?")[0])
            # sempre drena o corpo: sobra de bytes quebra o keep-alive
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            body = self.rfile.read(length) if length > 0 else b""

            if path == "/login":
                self._handle_login(body)
                return

            if not self._authed():
                self._send(401, b"unauthorized", "text/plain")
                return

            if path == "/api/config":
                self._handle_save_config(body)
                return

            if path == "/api/preview":
                self._handle_preview(body)
                return

            if path == "/api/purge":
                from .maintenance import purge as run_purge

                try:
                    payload = json.loads(body or b"{}")
                    report = run_purge(cfg, db, dry_run=bool(payload.get("dry_run")))
                    self._send(200, json.dumps(report, ensure_ascii=False).encode(),
                               "application/json; charset=utf-8")
                except Exception as exc:
                    self._send(500, json.dumps({"error": str(exc)}).encode(),
                               "application/json; charset=utf-8")
                return

            mtpl = re.match(r"^/api/templates/([^/]+)$", path)
            if mtpl:
                self._handle_save_template(unquote(mtpl.group(1)), body)
                return

            mstpl = re.match(r"^/api/streams/([^/]+)/template$", path)
            if mstpl:
                try:
                    payload = json.loads(body or b"{}")
                    db.set_template(unquote(mstpl.group(1)), payload.get("template"))
                    self._send(200, b'{"ok":true}', "application/json; charset=utf-8")
                except Exception as exc:
                    self._send(400, json.dumps({"ok": False, "error": str(exc)}).encode(),
                               "application/json; charset=utf-8")
                return

            m = re.match(r"^/api/clip/(\d+)/feedback$", path)
            if not m:
                if path == "/api/streams":
                    self._handle_add_stream(body)
                    return
                mstop = re.match(r"^/api/streams/([^/]+)/stop$", path)
                if mstop:
                    slug = mstop.group(1)
                    db.set_stream_status(slug, "stopped")
                    body_out = json.dumps({"ok": True, "slug": slug}).encode()
                    self._send(200, body_out, "application/json; charset=utf-8")
                    return
                mpub = re.match(r"^/api/clip/(\d+)/publish$", path)
                if mpub:
                    from .publish import publish_clip

                    try:
                        state = publish_clip(db, cfg, int(mpub.group(1)))
                        code = 202
                    except Exception as exc:
                        state = {"state": "error", "error": str(exc)}
                        code = 400
                    self._send(code, json.dumps(state).encode(), "application/json; charset=utf-8")
                    return
                self._send(404, b"not found", "text/plain")
                return
            try:
                payload = json.loads(body or b"{}")
                vote = int(payload.get("vote", 0))
            except Exception:
                self._send(400, b"bad body", "text/plain")
                return
            ok = db.set_feedback(int(m.group(1)), vote)
            stats = db.feedback_stats()
            body = json.dumps({"ok": ok, **stats}).encode("utf-8")
            self._send(200 if ok else 404, body, "application/json; charset=utf-8")

        def _handle_add_stream(self, body: bytes) -> None:
            from .streams import add

            try:
                payload = json.loads(body or b"{}")
                url = str(payload.get("url") or "").strip()
                title = str(payload.get("title") or "").strip()
                platform = payload.get("platform") or None
                slug, sid = add(db, url, platform, title)
            except ValueError as exc:
                self._send(400, json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json; charset=utf-8")
                return
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json; charset=utf-8")
                return
            out = json.dumps({"ok": True, "slug": slug, "id": sid}).encode()
            self._send(200, out, "application/json; charset=utf-8")

        def do_DELETE(self) -> None:  # noqa: N802
            path = unquote(self.path.split("?")[0])
            try:
                length = int(self.headers.get("Content-Length") or 0)
                if length:
                    self.rfile.read(length)
            except ValueError:
                pass
            if not self._authed():
                self._send(401, b"unauthorized", "text/plain")
                return
            m = re.match(r"^/api/templates/([^/]+)$", path)
            if not m:
                self._send(404, b"not found", "text/plain")
                return
            from pipeline.util import ROOT, load_json
            from .templates import delete as delete_template

            try:
                name = unquote(m.group(1))
                cfg_path = ROOT / "config.json"
                current = load_json(cfg_path, {}) or {}
                if not delete_template(current, name):
                    self._send(400, b'{"ok":false,"error":"template default"}',
                               "application/json; charset=utf-8")
                    return
                cfg_path.write_text(
                    json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                cfg.data = current
            except Exception as exc:
                self._send(400, json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json; charset=utf-8")
                return
            self._send(200, b'{"ok":true}', "application/json; charset=utf-8")

        def _handle_save_config(self, body: bytes) -> None:
            from pipeline.util import ROOT, load_json

            try:
                payload = json.loads(body or b"{}")
                if not isinstance(payload, dict):
                    raise ValueError("config precisa ser um objeto")
                path = ROOT / "config.json"
                current = load_json(path, {}) or {}
                merged = _deep_merge(current, payload)
                merged = _sanitize_config(merged)
                if path.exists():
                    (ROOT / "config.json.bak").write_text(
                        path.read_text(encoding="utf-8"), encoding="utf-8"
                    )
                path.write_text(
                    json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                cfg.data = merged
            except Exception as exc:
                self._send(400, json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json; charset=utf-8")
                return
            self._send(200, b'{"ok":true}', "application/json; charset=utf-8")

        def _handle_preview(self, body: bytes) -> None:
            from .template_preview import preview_png

            try:
                payload = json.loads(body or b"{}")
                png = preview_png(
                    cfg,
                    str(payload.get("template") or "default"),
                    hook=str(payload.get("hook") or "NAO E POSSIVEL"),
                    layout=str(payload.get("layout") or "pip"),
                    render_override=payload.get("render") or {},
                    branding_override=payload.get("branding") or {},
                )
            except Exception as exc:
                log(f"[preview] {exc}")
                png = None
            if not png:
                self._send(500, b"preview failed", "text/plain")
                return
            self._send(200, png, "image/png")

        def _handle_save_template(self, name: str, body: bytes) -> None:
            from pipeline.util import ROOT, load_json
            from .templates import save as save_template

            try:
                payload = json.loads(body or b"{}")
                path = ROOT / "config.json"
                current = load_json(path, {}) or {}
                save_template(path, current, name, payload or {})
                cfg.data = load_json(path, {}) or {}
            except Exception as exc:
                self._send(400, json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json; charset=utf-8")
                return
            self._send(200, b'{"ok":true}', "application/json; charset=utf-8")

        def _handle_login(self, body: bytes) -> None:
            from urllib.parse import parse_qs

            try:
                form = parse_qs(body.decode("utf-8", "replace"))
            except Exception:
                self._send(400, b"bad body", "text/plain")
                return
            password = (form.get("password") or [""])[0]
            ip = self.client_address[0] if self.client_address else "?"
            ok, result = auth.login(ip, password) if auth else (False, "auth indisponivel")
            if ok:
                self._redirect("/", _cookie(result, cookie_secure, auth.ttl))
                return
            msg = f'<div class="err">{result}</div>'
            body = LOGIN_PAGE.replace("{erro}", msg).encode("utf-8")
            self._send(200, body, "text/html; charset=utf-8")

        def _serve_preview(self, path: str) -> None:
            slug = path.rsplit("/", 1)[-1].removesuffix(".mp4")
            known = {r["slug"] for r in db.streams(None)}
            if slug not in known:
                self._send(404, b"unknown stream", "text/plain")
                return
            from .preview import ensure

            file = ensure(cfg, slug)
            if not file or not file.exists():
                self._send(204, b"", "video/mp4")
                return
            self._send(200, file.read_bytes(), "video/mp4")

        def _serve_media(self, path: str) -> None:
            name = path.rsplit("/", 1)[-1]
            stem, _, ext = name.partition(".")
            try:
                clip_id = int(stem)
            except ValueError:
                self._send(400, b"bad id", "text/plain")
                return
            row = db.clip(clip_id)
            if not row or not row["path"]:
                self._send(404, b"clip not found", "text/plain")
                return

            target = Path(row["path"])
            if ext == "jpg":
                target = target.with_suffix(".jpg")
            if not target.exists() or not target.resolve().is_relative_to(out_dir):
                self._send(404, b"file missing", "text/plain")
                return

            data = target.read_bytes()
            ctype = "video/mp4" if ext == "mp4" else "image/jpeg"
            self._send(200, data, ctype, cache=True)

    return Handler


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request: Any, client_address: Any) -> None:
        """Cliente fechando conexao (reload da pagina, video trocando) nao e erro."""
        return


def serve(
    cfg: Any,
    db: DB,
    port: int = 8787,
    open_browser: bool = True,
    host: str = "127.0.0.1",
    auth: Any = None,
    cookie_secure: bool = False,
) -> None:
    httpd = _Server((host, port), _handler(cfg, db, auth, cookie_secure))
    shown = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    url = f"http://{shown}:{port}/"
    if auth is not None and auth.enabled:
        log(f"[painel] {url}  (senha ativa, ctrl+c para sair)")
    else:
        log(f"[painel] {url}  (SEM SENHA — apenas local)")
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("[painel] encerrado")
    finally:
        httpd.server_close()
