"""Painel: cards de estado, lives monitoradas e clipes gerados."""

HOME_PAGE = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>cortai — painel</title>
<style>
:root{--bg:#0b0c0f;--panel:#101216;--card:#15171c;--line:#23262e;--line2:#2c303a;--fg:#e8eaed;--dim:#8b929e;--faint:#5a616d;--acc:#ffd400;--ok:#3ddc84;--bad:#ff5c5c;--blue:#6ea8ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.5 ui-sans-serif,system-ui,Segoe UI,Roboto,sans-serif;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
button,input,select{font-family:inherit}

header.top{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:10px;height:52px;padding:0 18px;background:rgba(11,12,15,.92);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:baseline;gap:6px;font-weight:650;font-size:14px;letter-spacing:-.01em}
.brand b{color:var(--acc);font-weight:700}
.pill{font-size:11px;padding:4px 10px;border-radius:99px;border:1px solid var(--line2);color:var(--dim);white-space:nowrap}
.pill.live{color:var(--ok);border-color:rgba(61,220,132,.35);background:rgba(61,220,132,.06)}
.pill.warn{color:var(--acc);border-color:rgba(255,212,0,.3)}
.grow{flex:1}
.clock{font-size:11px;color:var(--faint);font-variant-numeric:tabular-nums}
.btn{display:inline-flex;align-items:center;gap:7px;height:32px;padding:0 13px;border-radius:8px;border:1px solid var(--line2);background:#191c22;color:var(--fg);font-size:12px;font-weight:550;cursor:pointer;transition:.15s}
.btn:hover{border-color:#3d4351;background:#1e222a}
.btn.primary{background:#1d2530;border-color:#33405a;color:#cfe1ff}
.btn.primary:hover{background:#232d3b}

main{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:20px;padding:18px 20px 70px;align-items:start;max-width:1600px;margin:0 auto}
@media(max-width:1100px){main{grid-template-columns:1fr}}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:22px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:13px 15px;display:grid;gap:2px;min-width:0}
.stat .k{font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint)}
.stat strong{font-size:23px;font-weight:650;letter-spacing:-.02em;line-height:1.15}
.stat .sub{font-size:11px;color:var(--dim);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.stat.good strong{color:var(--ok)}
.stat.bad strong{color:var(--bad)}
.stat.warn strong{color:var(--acc)}

h2.sec{display:flex;align-items:center;gap:10px;font-size:11px;letter-spacing:.13em;text-transform:uppercase;color:var(--faint);margin:0 0 10px;font-weight:600}
h2.sec span{font-weight:400;letter-spacing:0;text-transform:none;font-size:11.5px;color:var(--faint)}

.addlive{display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap}
.addlive input{flex:1 1 240px;min-width:0;height:34px;padding:0 12px;border-radius:9px;border:1px solid var(--line2);background:#0e1014;color:var(--fg);font-size:12.5px}
.addlive input:focus{outline:none;border-color:#414958;box-shadow:0 0 0 3px rgba(110,168,255,.08)}
.addlive button{height:34px;padding:0 16px;border-radius:9px;border:1px solid #33405a;background:#1d2530;color:#cfe1ff;font-weight:600;cursor:pointer;font-size:12.5px}
.addlive button:hover{background:#232d3b}

.streams{display:grid;gap:10px;margin-bottom:26px}
.stream{background:var(--panel);border:1px solid var(--line);border-radius:13px;padding:10px;display:flex;gap:12px;align-items:center;transition:border-color .15s}
.stream:hover{border-color:var(--line2)}
.pv{width:184px;aspect-ratio:16/9;border-radius:9px;background:#000;object-fit:cover;flex:0 0 auto;display:block}
.sinfo{flex:1 1 auto;min-width:0;display:grid;gap:7px}
.srow{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.dot{width:8px;height:8px;border-radius:99px;background:var(--bad);flex:0 0 auto}
.dot.on{background:var(--ok);box-shadow:0 0 0 4px rgba(61,220,132,.12)}
.sname{font-weight:600;font-size:13px}
.meta{color:var(--dim);font-size:11.5px;white-space:nowrap}
.bar{height:4px;background:#1b1e24;border-radius:99px;overflow:hidden;flex:1 1 120px;min-width:90px}
.bar i{display:block;height:100%;background:var(--acc);transition:width .4s;border-radius:99px}
.kill{margin-left:auto;background:none;border:1px solid var(--line);color:var(--faint);border-radius:7px;padding:4px 10px;cursor:pointer;font-size:11.5px}
.kill:hover{border-color:rgba(255,92,92,.45);color:#ffb4b4}
.kill.del{margin-left:0}
.kill.del:hover{border-color:rgba(255,92,92,.6);background:rgba(255,92,92,.09);color:#ffb4b4}

.accs{display:block}
.acc{background:var(--panel);border:1px solid var(--line);border-radius:13px;margin-bottom:10px;overflow:hidden}
.acc>summary{display:flex;align-items:center;gap:10px;padding:11px 14px;cursor:pointer;list-style:none;user-select:none}
.acc>summary::-webkit-details-marker{display:none}
.acc>summary:hover{background:#12141a}
.acc-dot{width:8px;height:8px;border-radius:99px;background:#3a3f4a;flex:0 0 auto}
.acc-dot.on{background:var(--ok);box-shadow:0 0 0 4px rgba(61,220,132,.12)}
.acc-name{font-weight:600;font-size:13px}
.acc-n{font-size:10.5px;color:var(--faint);border:1px solid var(--line2);border-radius:99px;padding:1px 8px;font-variant-numeric:tabular-nums}
.acc-when{margin-left:auto;font-size:11px;color:var(--faint);font-variant-numeric:tabular-nums}
.acc-arrow{color:var(--faint);font-size:10px;transition:transform .18s}
.acc[open] .acc-arrow{transform:rotate(180deg)}
.acc[open]>summary{border-bottom:1px solid var(--line)}
.acc .clips{padding:12px}

.clips{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:14px}
.clip{background:var(--panel);border:1px solid var(--line);border-radius:13px;overflow:hidden;transition:border-color .15s,transform .15s}
.clip:hover{border-color:var(--line2);transform:translateY(-1px)}
.thumbwrap{position:relative;aspect-ratio:9/16;background:#0d0f13;cursor:pointer;overflow:hidden}
.thumbwrap img{width:100%;height:100%;object-fit:cover;display:block}
.nocap{position:absolute;inset:0;display:grid;place-items:center;color:#333844;font-size:11px}
.badges{position:absolute;top:8px;left:8px;right:8px;display:flex;gap:6px;justify-content:space-between;align-items:flex-start}
.badge{font-size:10px;font-weight:700;padding:3px 7px;border-radius:6px;background:rgba(0,0,0,.72);letter-spacing:.03em;backdrop-filter:blur(4px)}
.badge.score{color:var(--acc)}.badge.layout{color:#9ad1ff}.badge.size{color:var(--dim);font-weight:500}
.clip .body{padding:10px 12px 12px}
.clip .t{font-weight:600;font-size:12.5px;line-height:1.35;margin-bottom:3px}
.clip .h{font-size:10.5px;color:var(--acc);margin-bottom:5px;letter-spacing:.02em}
.clip .c{font-size:11px;color:var(--dim);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.clip .tags{font-size:10px;color:#5c93c4;margin-top:6px;word-break:break-word;display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}
.clip .foot{display:flex;justify-content:space-between;margin-top:8px;font-size:10px;color:var(--faint)}
.vote{display:flex;gap:6px;margin-top:8px}
.vote button{flex:1;background:#181b21;border:1px solid var(--line);color:var(--faint);border-radius:7px;padding:5px 0;cursor:pointer;font-size:13px;transition:.15s}
.vote button:hover{border-color:var(--line2);color:var(--fg)}
.vote .up.on{background:rgba(61,220,132,.14);border-color:rgba(61,220,132,.45);color:var(--ok)}
.vote .dn.on{background:rgba(255,92,92,.14);border-color:rgba(255,92,92,.45);color:var(--bad)}
.pub{display:block;width:100%;margin-top:6px;padding:6px 0;border-radius:7px;border:1px solid var(--line2);background:#181b21;color:var(--dim);font-size:11px;text-align:center;text-decoration:none;cursor:pointer}
.pub:hover{border-color:#3d4351;color:var(--fg)}
.pub.done{color:var(--ok);border-color:rgba(61,220,132,.35)}
.pub.up{color:var(--acc);border-color:rgba(255,212,0,.3)}
.pub.err{color:var(--bad);border-color:rgba(255,92,92,.35)}

aside{display:grid;gap:14px;position:sticky;top:72px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:13px;overflow:hidden}
.panel .ph{padding:10px 13px;border-bottom:1px solid var(--line);font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:var(--faint);font-weight:600}
.log{max-height:330px;overflow:auto;padding:8px 10px;font:11px/1.6 ui-monospace,Consolas,monospace}
.log div{display:flex;gap:8px;white-space:pre-wrap;word-break:break-word}
.log time{color:#474e5a;flex:0 0 auto;font-variant-numeric:tabular-nums}
.log .err{color:#ff9b9b}.log .warn{color:var(--acc)}.log .score{color:var(--ok)}
.empty{padding:26px;text-align:center;color:#3f4652;font-size:12px}
dialog{border:none;background:transparent;padding:0;max-width:min(92vw,420px)}
dialog::backdrop{background:rgba(0,0,0,.82)}
dialog video{width:100%;border-radius:12px;display:block}
dialog button{position:absolute;top:-34px;right:0;background:none;border:none;color:#fff;font-size:22px;cursor:pointer}
</style></head>
<body>
<header class="top">
  <span class="brand">cortai <b>·</b></span>
  <span class="pill" id="live-pill">—</span>
  <span class="pill" id="clip-pill">—</span>
  <span class="pill" id="cost-pill">—</span>
  <span class="pill" id="fb-pill">—</span>
  <span class="grow"></span>
  <span class="clock" id="clock">—</span>
  <a class="btn primary" href="/settings" title="Configurações">⚙ Configurações</a>
</header>

<main>
  <div>
    <div class="stats">
      <div class="stat" id="st-live"><span class="k">No ar</span><strong id="s-live">–</strong><span class="sub" id="s-livesub">—</span></div>
      <div class="stat"><span class="k">Clipes</span><strong id="s-clips">–</strong><span class="sub" id="s-clipsub">—</span></div>
      <div class="stat"><span class="k">Custo hoje</span><strong id="s-cost">–</strong><span class="sub" id="s-costsub">—</span></div>
      <div class="stat"><span class="k">Fila de publicação</span><strong id="s-queue">–</strong><span class="sub" id="s-queuesub">—</span></div>
    </div>

    <h2 class="sec">Lives monitoradas</h2>
    <form class="addlive" id="addform">
      <input id="newurl" placeholder="https://www.twitch.tv/canal" required>
      <input id="newtitle" placeholder="Título (opcional)">
      <button type="submit">Adicionar</button>
    </form>
    <div class="streams" id="streams"></div>

    <h2 class="sec">clipes <span id="clipsub"></span></h2>
    <div class="accs" id="clips"></div>
  </div>

  <aside>
    <div class="panel"><div class="ph">candidatos</div><div class="log" id="cands"></div></div>
    <div class="panel"><div class="ph">eventos</div><div class="log" id="logs"></div></div>
  </aside>
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
  const name=document.createElement('span');name.className='sname';
  const meta=document.createElement('span');meta.className='meta';
  row1.append(dot,name,meta);
  const row2=document.createElement('div');row2.className='srow';
  const bar=document.createElement('span');bar.className='bar';
  const fill=document.createElement('i');bar.append(fill);
  const mBuf=document.createElement('span');mBuf.className='meta';
  const mFace=document.createElement('span');mFace.className='meta';
  const mClips=document.createElement('span');mClips.className='meta';
  const kill=document.createElement('button');kill.className='kill';kill.textContent='parar';
  const del=document.createElement('button');del.className='kill del';del.textContent='remover';
  row2.append(bar,mBuf,mFace,mClips,kill,del);
  info.append(row1,row2);root.append(vid,info);
  return {root,vid,dot,name,meta,fill,mBuf,mFace,mClips,kill,del,previewAt:null};
}

function renderStreams(list){
  const host=document.getElementById('streams');
  if(!list.length){host.innerHTML='<div class="empty">Nenhuma live cadastrada</div>';cards.clear();return}
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
    c.mFace.textContent=s.facecam?('Facecam '+(s.facecam.w|0)+'px'):'Sem facecam';
    c.mClips.textContent=s.clips+' clipes';
    c.kill.onclick=()=>stopStream(s.slug);
    c.kill.style.display=s.status==='active'?'block':'none';
    c.del.onclick=()=>removeStream(s.slug, s.clips);
    if(s.preview_at && c.previewAt!==s.preview_at){
      c.previewAt=s.preview_at;
      c.vid.src=s.preview_url+'?t='+s.preview_at;
      const p=c.vid.play();if(p&&p.catch)p.catch(()=>{});
    }
  }
  for(const [slug,c] of cards){if(!seen.has(slug)){c.root.remove();cards.delete(slug)}}
}

function publishControl(c){
  const p=c.published||{};
  if(p.state==='done') return '<a class="pub done" href="'+esc(p.url||'#')+'" target="_blank" rel="noopener">No YouTube ✓</a>';
  if(p.state==='uploading'){const pct=p.progress?Math.round(p.progress*100):0;return '<span class="pub up">Enviando '+pct+'%</span>';}
  if(p.state==='queued') return '<span class="pub up">'+(p.scheduled_for?'Agendado':'Na fila')+'</span>';
  if(p.state==='error') return '<button class="pub err" onclick="publishClip('+c.id+')" title="'+esc(p.error||'')+'">Reenviar</button>';
  if(!window.CAN_PUBLISH) return '';
  return '<button class="pub" onclick="publishClip('+c.id+')">Publicar no YouTube</button>';
}

function clipCard(c){
  const thumb=c.has_thumb? '<img loading="lazy" src="'+c.thumb_url+'?t='+c.id+'" alt="">':'<div class="nocap">Sem preview</div>';
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
      '<button class="dn'+(c.feedback===-1?' on':'')+'" onclick="vote('+c.id+',-1)" title="não presta">👎</button>'+
    '</div>'+publishControl(c)+'</div></div>';
}

const openSlugs=new Set();
let clipsStarted=false;

function renderClips(list, streams){
  const host=document.getElementById('clips');
  const live=new Set(streams.filter(s=>s.live).map(s=>s.slug));
  const order=streams.map(s=>s.slug);

  const groups=new Map();
  for(const s of order) groups.set(s, []);
  for(const c of list){
    const k=c.slug||'sem canal';
    if(!groups.has(k)) groups.set(k,[]);
    groups.get(k).push(c);
  }
  if(!groups.size){
    host.innerHTML='<div class="empty">Nenhum clipe ainda. O sistema espera o buffer encher e um pico de energia.</div>';
    return;
  }
  const keys=[...groups.keys()].sort((a,b)=>{
    const ia=order.indexOf(a), ib=order.indexOf(b);
    return (ia<0?999:ia)-(ib<0?999:ib);
  });
  if(!clipsStarted){ openSlugs.add(keys[0]); clipsStarted=true; }

  host.innerHTML=keys.map(k=>{
    const items=groups.get(k);
    const isOpen=openSlugs.has(k);
    const corpo=items.length
      ? '<div class="clips">'+items.map(clipCard).join('')+'</div>'
      : '<div class="empty" style="padding:18px">Nenhum clipe deste canal ainda</div>';
    return '<details class="acc" data-slug="'+esc(k)+'"'+(isOpen?' open':'')+'>'+
      '<summary><span class="acc-dot'+(live.has(k)?' on':'')+'"></span>'+
        '<span class="acc-name">'+esc(k)+'</span>'+
        '<span class="acc-n">'+items.length+'</span>'+
        '<span class="acc-when">'+esc(items.length?items[0].when:'')+'</span>'+
        '<span class="acc-arrow">▼</span></summary>'+corpo+'</details>';
  }).join('');

  host.querySelectorAll('details.acc').forEach(d=>{
    d.addEventListener('toggle',()=>{
      if(d.open) openSlugs.add(d.dataset.slug); else openSlugs.delete(d.dataset.slug);
    });
  });
}

function render(d){
  window.CAN_PUBLISH=!!(d.publish&&d.publish.ready);

  const lives=d.streams.filter(s=>s.live).length;
  const total=d.streams.length;
  document.getElementById('live-pill').textContent=lives+'/'+total+' no ar';
  document.getElementById('live-pill').className='pill'+(lives?' live':'');
  document.getElementById('clip-pill').textContent=d.totals.clips+' clipes';
  document.getElementById('clip-pill').className='pill';
  document.getElementById('clock').textContent=new Date().toLocaleTimeString('pt-BR');

  const hoje=d.cost&&d.cost.hoje||{};
  const cp=document.getElementById('cost-pill');
  cp.textContent='US$ '+(hoje.usd||0).toFixed(2)+' · R$ '+(hoje.brl||0).toFixed(2);
  cp.title='total: US$ '+((d.cost&&d.cost.total&&d.cost.total.usd)||0).toFixed(2)
    +' | ASR US$ '+(hoje.by_kind&&hoje.by_kind.asr||0).toFixed(2)
    +' | LLM US$ '+(hoje.by_kind&&hoje.by_kind.llm||0).toFixed(2)
    +' | '+(hoje.calls||0)+' chamadas';
  const fb=d.feedback||{};
  const fp=document.getElementById('fb-pill');
  fp.textContent=fb.rated?('precisão '+Math.round(fb.precision*100)+'%'):'Sem avaliação';
  fp.className='pill'+(fb.rated&&fb.precision>=0.7?' live':'');
  fp.title=fb.rated?(fb.good+' 👍 · '+fb.bad+' 👎'):'avalie os clipes para medir a precisão';

  // cards de estado
  const liveEl=document.getElementById('st-live');
  document.getElementById('s-live').textContent=lives+'/'+total;
  liveEl.className='stat'+(lives>0?' good':'');
  document.getElementById('s-livesub').textContent=lives?('Capturando '+d.streams.filter(s=>s.live).map(s=>s.slug).join(', ')):'Nenhuma no ar';

  const clipsToday=(d.clips||[]).filter(c=>c.when&&true).length;
  document.getElementById('s-clips').textContent=d.totals.clips;
  const pub=d.published_today||0; document.getElementById('s-clipsub').textContent=pub+' '+(pub===1?'publicado':'publicados')+' hoje';

  document.getElementById('s-cost').textContent='R$ '+(hoje.brl||0).toFixed(2);
  document.getElementById('s-costsub').textContent=((hoje.calls||0))+' chamadas de API hoje';

  const q=d.queue_pending||0;
  document.getElementById('s-queue').textContent=q;
  document.getElementById('s-queuesub').textContent=(d.auto_publish&&d.auto_publish.enabled)
    ? 'Auto ≥'+d.auto_publish.min_score+' ('+d.auto_publish.privacy+')'
    : 'Publicação automática desligada';

  renderStreams(d.streams);

  document.getElementById('clipsub').textContent=d.clips.length?(d.clips.length+' recentes'):'';
  renderClips(d.clips, d.streams);

  document.getElementById('cands').innerHTML = d.candidates.length? d.candidates.map(c=>{
    const m=c.msg||''; const keep=/keep=True/.test(m);
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
  }catch(e){document.getElementById('live-pill').textContent='Servidor fora';}
}
async function vote(id,v){
  try{
    const r=await fetch('/api/clip/'+id+'/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({vote:v})});
    if(!r.ok) return;
    lastJson='';tick();
  }catch(e){}
}
async function publishClip(id){
  const r=await fetch('/api/clip/'+id+'/publish',{method:'POST'});
  const j=await r.json().catch(()=>({}));
  if(j.error) alert(j.error);
  lastJson='';tick();
}
async function stopStream(slug){
  if(!confirm('Parar '+slug+'?')) return;
  await fetch('/api/streams/'+encodeURIComponent(slug)+'/stop',{method:'POST'});
  lastJson='';tick();
}
async function removeStream(slug, clips){
  const aviso='Remover '+slug+'?\n\nVai apagar o canal, '+clips+' clipe(s), as miniaturas e o buffer em disco.'
    +'\nO que já foi publicado no YouTube continua lá. Não dá para desfazer.';
  if(!confirm(aviso)) return;
  const r=await fetch('/api/streams/'+encodeURIComponent(slug),{method:'DELETE'});
  const j=await r.json().catch(()=>({}));
  if(!j.ok){ alert('Erro ao remover: '+(j.error||r.status)); return; }
  openSlugs.delete(slug);
  cards.delete(slug);
  lastJson=''; tick();
}
document.getElementById('addform').addEventListener('submit', async (e)=>{
  e.preventDefault();
  const url=document.getElementById('newurl'), title=document.getElementById('newtitle');
  const r=await fetch('/api/streams',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({url:url.value.trim(), title:title.value.trim()})});
  const j=await r.json().catch(()=>({}));
  if(!j.ok){ alert('Erro: '+(j.error||r.status)); return; }
  url.value=''; title.value='';
  lastJson=''; tick();
});
function play(url){document.getElementById('v').src=url;document.getElementById('player').showModal()}
function closePlayer(){const v=document.getElementById('v');v.pause();v.src='';document.getElementById('player').close()}
tick();setInterval(tick,3000);
</script></body></html>"""
