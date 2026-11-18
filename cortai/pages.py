"""Pagina de configuracoes: nav a esquerda, linhas com controle a direita, preview fixo."""

SETTINGS_PAGE = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>cortai — configurações</title>
<style>
:root{--bg:#0b0c0f;--panel:#101216;--card:#15171c;--line:#23262e;--line2:#2c303a;--fg:#e8eaed;--dim:#8b929e;--faint:#5a616d;--acc:#ffd400;--ok:#3ddc84;--bad:#ff5c5c;--blue:#6ea8ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.5 ui-sans-serif,system-ui,Segoe UI,Roboto,sans-serif;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
button,input,select{font-family:inherit}

header.top{position:sticky;top:0;z-index:20;display:flex;align-items:center;gap:14px;height:52px;padding:0 18px;background:rgba(11,12,15,.92);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:baseline;gap:6px;font-weight:650;font-size:14px;letter-spacing:-.01em}
.brand b{color:var(--acc);font-weight:700}
.crumb{color:var(--faint);font-size:12px}
.crumb a{color:var(--dim)}.crumb a:hover{color:var(--fg)}
.grow{flex:1}
.btn{display:inline-flex;align-items:center;gap:6px;height:32px;padding:0 13px;border-radius:8px;border:1px solid var(--line2);background:#191c22;color:var(--fg);font-size:12px;font-weight:550;cursor:pointer;transition:.15s}
.btn:hover{border-color:#3d4351;background:#1e222a}
.btn.primary{background:#20301f;border-color:rgba(61,220,132,.45);color:#b9f5d0}
.btn.danger{color:#ffb4b4;border-color:rgba(255,92,92,.35)}
.btn.danger:hover{background:rgba(255,92,92,.1)}

main{display:grid;grid-template-columns:196px minmax(0,1fr) 360px;gap:22px;padding:20px 22px 90px;align-items:start;max-width:1560px;margin:0 auto}
@media(max-width:1280px){main{grid-template-columns:180px minmax(0,1fr)} aside.preview{grid-column:1/-1;display:grid;grid-template-columns:minmax(0,320px) 1fr;gap:16px;align-items:start}}
@media(max-width:820px){main{grid-template-columns:1fr} nav.side{position:static;display:flex;overflow:auto;gap:4px;padding-bottom:6px}}

nav.side{position:sticky;top:72px;display:grid;gap:2px}
nav.side .grp{font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:var(--faint);padding:12px 10px 6px}
nav.side a{padding:7px 10px;border-radius:7px;color:var(--dim);font-size:12.5px;white-space:nowrap}
nav.side a:hover{background:#16191f;color:var(--fg)}
nav.side a.on{background:#1b1e25;color:var(--fg);font-weight:550}

section.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;margin-bottom:18px;scroll-margin-top:70px;overflow:hidden}
section.card>header{display:flex;align-items:baseline;gap:10px;padding:16px 20px 0}
section.card>header h2{margin:0;font-size:14px;font-weight:600;letter-spacing:-.01em}
section.card>header p{margin:0;color:var(--faint);font-size:12px}
section.card>.body{padding:4px 20px 18px}

.frow{display:grid;grid-template-columns:minmax(0,1fr) 190px;gap:18px;align-items:center;padding:12px 0;border-bottom:1px solid rgba(35,38,46,.7)}
.frow:last-child{border-bottom:none}
.frow .lab{min-width:0}
.frow .lab label{display:block;font-size:12.5px;color:var(--fg);font-weight:500}
.frow .lab .hint{display:block;color:var(--faint);font-size:11.5px;margin-top:2px}
.inp,select.inp{width:100%;height:34px;padding:0 10px;border-radius:8px;border:1px solid var(--line2);background:#0e1014;color:var(--fg);font-size:12.5px}
.inp:focus{outline:none;border-color:#4a5near}
.inp:focus{border-color:#414958;box-shadow:0 0 0 3px rgba(110,168,255,.08)}
select.inp{appearance:none;background-image:linear-gradient(45deg,transparent 50%,#7b8493 50%),linear-gradient(135deg,#7b8391 50%,transparent 50%);background-position:calc(100% - 15px) 14px,calc(100% - 10px) 14px;background-size:5px 5px,5px 5px;background-repeat:no-repeat}
input[type=color].inp{padding:3px;height:34px;cursor:pointer}

.sw{position:relative;display:inline-flex;width:40px;height:22px;flex:0 0 auto;justify-self:end}
.sw input{opacity:0;width:0;height:0}
.sw span{position:absolute;inset:0;background:#2a2f38;border-radius:99px;transition:.18s;cursor:pointer}
.sw span::after{content:"";position:absolute;top:3px;left:3px;width:16px;height:16px;border-radius:99px;background:#8b929e;transition:.18s}
.sw input:checked+span{background:rgba(61,220,132,.3)}
.sw input:checked+span::after{transform:translateX(18px);background:var(--ok)}

aside.preview{position:sticky;top:72px;display:grid;gap:12px}
.pv{background:#000;border:1px solid var(--line);border-radius:14px;overflow:hidden;aspect-ratio:9/16;display:grid;place-items:center;position:relative}
.pv img{width:100%;height:100%;object-fit:contain;display:block}
.pv .ph{position:absolute;color:var(--faint);font-size:11px}
.mini{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px}
.mini .t{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--faint);margin-bottom:8px}
.mini .row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.mini .row.full{grid-template-columns:1fr}
.mini .row>*{min-width:0}

.savebar{position:fixed;left:0;right:0;bottom:0;z-index:30;display:flex;align-items:center;gap:12px;padding:10px 22px;background:rgba(11,12,15,.94);backdrop-filter:blur(10px);border-top:1px solid var(--line)}
.savebar .st{font-size:12px;color:var(--faint)}
.savebar .st.dirty{color:var(--acc)}
#toast{position:fixed;bottom:64px;left:50%;transform:translateX(-50%) translateY(8px);background:#1b1e25;border:1px solid var(--line2);padding:9px 16px;border-radius:9px;font-size:12px;opacity:0;transition:.2s;pointer-events:none;z-index:40}
#toast.on{opacity:1;transform:translateX(-50%) translateY(0)}
</style></head>
<body>
<header class="top">
  <span class="brand">cortai <b>·</b></span>
  <span class="crumb"><a href="/">Painel</a> / configurações</span>
  <span class="grow"></span>
  <select id="tpl" class="btn" style="padding-right:26px"></select>
  <button class="btn" onclick="newTemplate()">Novo template</button>
  <button class="btn danger" onclick="delTemplate()">Excluir</button>
  <button class="btn primary" onclick="saveAll()">Salvar</button>
</header>

<main>
  <nav class="side" id="nav"></nav>
  <div id="forms"></div>
  <aside class="preview">
    <div class="pv"><img id="preview" alt=""><span class="ph" id="ph">Gerando preview…</span></div>
    <div class="mini">
      <div class="t">Prévia</div>
      <div class="row full" style="margin-bottom:8px">
        <input id="hook" class="inp" value="NAO E POSSIVEL" placeholder="Gancho do exemplo">
      </div>
      <div class="row" style="margin-bottom:8px">
        <select id="layout" class="inp"><option value="pip">pip</option><option value="face">face</option><option value="game">game</option></select>
        <select id="assign" class="inp"></select>
      </div>
      <div class="row">
        <button class="btn" onclick="applyTemplate()">Aplicar na live</button>
        <button class="btn" onclick="saveAsTemplate()">Salvar template</button>
      </div>
    </div>
    <div class="mini">
      <div class="t">Limpeza de disco</div>
      <div class="row">
        <button class="btn" onclick="runPurge(true)">Simular</button>
        <button class="btn danger" onclick="runPurge(false)">Limpar agora</button>
      </div>
      <div id="purgeout" style="color:var(--faint);font-size:11px;margin-top:8px">Respeita a retenção configurada</div>
    </div>
  </aside>
</main>

<div class="savebar"><span class="st" id="status">Tudo salvo</span><span class="grow"></span><button class="btn" onclick="reloadConfig()">Descartar</button><button class="btn primary" onclick="saveAll()">Salvar alterações</button></div>
<div id="toast"></div>

<script>
let S=null, streams=[], tplName='default', dirty=false;
const F=[];

function sec(id, title, hint, items){F.push({id,title:cap(title),hint:cap(hint),items:items.map(i=>({...i,l:cap(i.l),h:i.h?cap(i.h):i.h}))});}
function cap(s){ if(!s) return s; return s.charAt(0).toUpperCase()+s.slice(1); }
function g(p){return p.split('.').reduce((o,k)=>(o==null?undefined:o[k]),S);}
function s(p,v){const ks=p.split('.');let o=S;for(let i=0;i<ks.length-1;i++){o[ks[i]]=o[ks[i]]||{};o=o[ks[i]];}o[ks[ks.length-1]]=v;}
function hexToNum(h){return '0x'+String(h||'#FFD400').replace('#','').toUpperCase();}
function numToHex(v){return '#'+String(v||'0xFFD400').replace(/^0x/i,'').slice(-6);}

function buildSchema(){
  F.length=0;
  sec('captura','Captura','quanto tempo de live fica em memória e de quanto em quanto tempo o sistema olha',
    [{p:'live.window_s',l:'janela de análise',h:'segundos que entram na análise; menor reage mais rápido',u:'s',t:'num',min:30,max:180},
     {p:'live.cycle_s',l:'intervalo entre análises',h:'de quanto em quanto tempo procura um pico',u:'s',t:'num',min:5,max:60},
     {p:'live.min_buffer_s',l:'buffer mínimo',h:'espera juntar isso antes da primeira análise',u:'s',t:'num',min:20,max:300},
     {p:'live.buffer_seconds',l:'buffer total em disco',h:'quanto de live fica gravado no anel',u:'s',t:'num',min:120,max:1800}]);

  sec('momento','Detecção de momento','como o sistema decide que algo aconteceu',
    [{p:'moments.peak_z',l:'sensibilidade',h:'1.3 é equilibrado; menor corta mais, maior corta menos',t:'num',step:0.1,min:0.3,max:4},
     {p:'moments.min_sep_s',l:'distância entre clipes',h:'evita dois cortes do mesmo evento',u:'s',t:'num',min:5,max:300},
     {p:'moments.context_pre_s',l:'contexto antes do pico',u:'s',t:'num',min:2,max:60},
     {p:'moments.context_post_s',l:'contexto depois do pico',u:'s',t:'num',min:5,max:90},
     {p:'moments.min_clip_s',l:'duração mínima do corte',u:'s',t:'num',min:5,max:60},
     {p:'moments.max_clip_s',l:'duração máxima do corte',u:'s',t:'num',min:10,max:90}]);

  sec('juiz','Classificador','o gate filtra barato; o LLM escreve a copy só dos aprovados',
    [{p:'classify.min_score',l:'nota mínima para aprovar',h:'0 a 10; abaixo disso o clipe é descartado',t:'num',step:0.5,min:0,max:10},
     {p:'classify.frames',l:'frames analisados',h:'quantos quadros o juiz vê por candidato',t:'num',min:1,max:10},
     {p:'classify.copy_frames',l:'frames na copy',h:'o juiz já viu; a copy precisa de menos',t:'num',min:0,max:8},
     {p:'classify.jev.model',l:'modelo do gate (Jev)',t:'text'},
     {p:'classify.jev.min_score',l:'gate: nota mínima',t:'num',step:0.5,min:0,max:10},
     {p:'classify.jev.min_event',l:'gate: evento mínimo',h:'probabilidade de haver evento visível',t:'num',step:0.05,min:0,max:1}]);

  sec('video','Vídeo','enquadramento, legenda e qualidade do arquivo final',
    [{p:'render.mode',l:'enquadramento',h:'pad_blur preserva o HUD; crop segue o movimento',t:'sel',opts:[['pad_blur','Barras desfocadas (pad_blur)'],['crop','Segue a ação (crop)']]},
     {p:'render.fps',l:'fps de saída',t:'num',min:15,max:60},
     {p:'render.crf',l:'qualidade (CRF)',h:'menor é melhor e mais pesado',t:'num',min:14,max:32},
     {p:'render.preset',l:'preset x264',t:'sel',opts:[['ultrafast','ultrafast'],['veryfast','veryfast'],['fast','fast'],['medium','medium']]},
     {p:'render.blur_sigma',l:'desfoque do fundo',t:'num',min:0,max:60},
     {p:'render.burn_subs',l:'queimar legenda',t:'bool'},
     {p:'render.karaoke_size',l:'legenda: tamanho',t:'num',min:40,max:140},
     {p:'render.karaoke_words',l:'legenda: palavras por vez',t:'num',min:1,max:6},
     {p:'render.karaoke_margin_v',l:'legenda: altura do rodapé',t:'num',min:40,max:700},
     {p:'render.hook_caption',l:'mostrar gancho',t:'bool'},
     {p:'render.hook_size',l:'gancho: tamanho',t:'num',min:40,max:160}]);

  sec('marca','Marca','identidade do canal dentro do vídeo',
    [{p:'branding.handle',l:'@ do canal',t:'text'},
     {p:'branding.cta',l:'chamada no rodapé',t:'text'},
     {p:'branding.accent',l:'cor de destaque',t:'color'},
     {p:'branding.logo',l:'logo',h:'caminho do PNG com transparência',t:'text'},
     {p:'branding.logo_position',l:'posição do logo',t:'sel',opts:[['tl','Topo esquerdo'],['tr','Topo direito'],['bl','Baixo esquerdo'],['br','Baixo direito']]},
     {p:'branding.logo_width',l:'largura do logo',u:'px',t:'num',min:60,max:600},
     {p:'branding.handle_offset',l:'distância do @ até o rodapé',u:'px',t:'num',min:0,max:800},
     {p:'branding.cta_offset',l:'distância do CTA até o rodapé',u:'px',t:'num',min:0,max:800},
     {p:'render.pip_scale',l:'facecam: tamanho',h:'fração da largura no layout pip',t:'num',step:0.01,min:0.15,max:0.6},
     {p:'render.pip_position',l:'facecam: canto',t:'sel',opts:[['tr','Topo direito'],['tl','Topo esquerdo'],['br','Baixo direito'],['bl','Baixo esquerdo']]},
     {p:'render.pip_offset_y',l:'facecam: altura',u:'px',t:'num',min:0,max:1200}]);

  sec('publicacao','Publicação','quando e como o clipe vai para o YouTube',
    [{p:'publish.auto',l:'publicar sozinho',h:'só clipes acima da nota mínima',t:'bool'},
     {p:'publish.auto_min_score',l:'nota mínima para publicar',h:'em 0–10: 8 publica só clipe nota 8+',t:'num',step:0.5,min:0,max:10},
     {p:'publish.privacy',l:'privacidade',t:'sel',opts:[['unlisted','Não listado'],['public','Público'],['private','Privado']]},
     {p:'publish.schedule_hours',l:'horários de postagem',h:'ex: 19,20 — vazio publica na hora',t:'list'},
     {p:'publish.max_attempts',l:'tentativas em caso de erro',t:'num',min:1,max:20},
     {p:'publish.retry_minutes',l:'espera entre tentativas',u:'min',t:'num',min:1,max:240},
     {p:'publish.category_id',l:'categoria do YouTube',h:'20 = Gaming',t:'text'},
     {p:'publish.description_footer',l:'rodapé da descrição',t:'text'}]);

  sec('manutencao','Manutenção','o que apagar e quando; clipe não publicado nunca sai',
    [{p:'maintenance.enabled',l:'limpeza automática',t:'bool'},
     {p:'maintenance.clip_retention_days',l:'apagar clipes publicados após',u:'dias',t:'num',min:1,max:3650},
     {p:'maintenance.keep_unpublished_days',l:'não publicado: guardar por',h:'0 = nunca apaga',t:'num',min:0,max:3650},
     {p:'maintenance.db_retention_days',l:'apagar log e custo após',u:'dias',t:'num',min:7,max:3650},
     {p:'maintenance.run_every_hours',l:'rodar a cada',u:'h',t:'num',min:1,max:168}]);

  sec('transcricao','Transcrição','ASR e vocabulário; trocar modelo exige reiniciar',
    [{p:'asr.language',l:'idioma',t:'text'},
     {p:'asr.models.openrouter',l:'modelo via OpenRouter',t:'text'},
     {p:'asr.models.groq',l:'modelo via Groq',t:'text'},
     {p:'asr.models.openai',l:'modelo via OpenAI',t:'text'},
     {p:'asr.keyterms',l:'termos do jogo',h:'vírgula; melhora nome próprio e gíria',t:'list'}]);
}

function control(it){
  const p=it.p, t=it.t||'text', v=g(p);
  if(t==='bool') return '<label class="sw"><input type="checkbox" data-p="'+p+'" data-t="bool" '+(v?'checked':'')+'><span></span></label>';
  if(t==='sel') return '<select class="inp" data-p="'+p+'" data-t="sel">'+it.opts.map(o=>'<option value="'+o[0]+'"'+(String(v)===o[0]?' selected':'')+'>'+o[1]+'</option>').join('')+'</select>';
  if(t==='color') return '<input class="inp" type="color" data-p="'+p+'" data-t="color" value="'+numToHex(v)+'">';
  if(t==='num') return '<input class="inp" type="number" data-p="'+p+'" data-t="num" value="'+(v==null?'':v)+'" '+(it.min!=null?'min="'+it.min+'" ':'')+(it.max!=null?'max="'+it.max+'" ':'')+(it.step?'step="'+it.step+'"':'')+(it.u?' placeholder="'+it.u+'"':'')+'>';
  if(t==='list') return '<input class="inp" type="text" data-p="'+p+'" data-t="list" value="'+((v||[]).join(', '))+'">';
  return '<input class="inp" type="text" data-p="'+p+'" data-t="text" value="'+(v==null?'':String(v).replace(/"/g,'&quot;'))+'">';
}

function buildForm(){
  document.getElementById('nav').innerHTML = '<div class="grp">Seções</div>' +
    F.map(f=>'<a href="#'+f.id+'" data-nav="'+f.id+'">'+f.title+'</a>').join('');
  document.getElementById('forms').innerHTML = F.map(f=>
    '<section class="card" id="'+f.id+'"><header><h2>'+f.title+'</h2><p>'+f.hint+'</p></header>'+
    '<div class="body">'+f.items.map(it=>
      '<div class="frow"><div class="lab"><label>'+it.l+'</label>'+(it.h?'<span class="hint">'+it.h+'</span>':'')+'</div>'+control(it)+'</div>'
    ).join('')+'</div></section>').join('');

  document.querySelectorAll('[data-p]').forEach(el=>{
    const ev = el.dataset.t==='bool' ? 'change' : 'input';
    el.addEventListener(ev,()=>{
      const p=el.dataset.p, t=el.dataset.t;
      let v=el.value;
      if(t==='num') v=Number(v);
      if(t==='bool') v=el.checked;
      if(t==='color') v=hexToNum(v);
      if(t==='list') v=String(v).split(',').map(x=>x.trim()).filter(Boolean);
      s(p,v); markDirty(); schedulePreview();
    });
  });

  const links=[...document.querySelectorAll('[data-nav]')];
  const obs=new IntersectionObserver(es=>{
    es.forEach(e=>{ if(e.isIntersecting){ links.forEach(a=>a.classList.toggle('on', a.dataset.nav===e.target.id)); } });
  },{rootMargin:'-70px 0px -60% 0px'});
  F.forEach(f=>{ const el=document.getElementById(f.id); if(el) obs.observe(el); });
}

function markDirty(){ dirty=true; const st=document.getElementById('status'); st.textContent='Alterações não salvas'; st.className='st dirty'; }

let tmr=null;
function schedulePreview(){clearTimeout(tmr);tmr=setTimeout(refreshPreview,450);}

async function refreshPreview(){
  const img=document.getElementById('preview'), ph=document.getElementById('ph');
  const body={template:tplName,hook:document.getElementById('hook').value,layout:document.getElementById('layout').value,render:{},branding:{}};
  ['mode','fps','crf','preset','blur_sigma','karaoke_size','karaoke_words','karaoke_margin_v','hook_size','hook_caption','burn_subs','pip_scale','pip_position','pip_offset_y'].forEach(k=>{ if(g('render.'+k)!==undefined) body.render[k]=g('render.'+k); });
  ['handle','cta','accent','logo','logo_position','logo_width','handle_offset','cta_offset'].forEach(k=>{ if(g('branding.'+k)!==undefined) body.branding[k]=g('branding.'+k); });
  try{
    const r=await fetch('/api/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r.ok){ph.textContent='Preview indisponível';ph.style.display='block';return;}
    img.src=URL.createObjectURL(await r.blob());
    ph.style.display='none';
  }catch(e){ ph.textContent='Preview falhou'; ph.style.display='block'; }
}

async function load(){
  S=await (await fetch('/api/config')).json();
  streams=(await (await fetch('/api/state')).json()).streams||[];
  const tpls=Object.keys(S.templates||{default:{}});
  const sel=document.getElementById('tpl');
  sel.innerHTML=tpls.map(t=>'<option>'+t+'</option>').join('');
  sel.value=tpls.includes(tplName)?tplName:tpls[0];
  tplName=sel.value;
  sel.onchange=()=>{tplName=sel.value;loadTemplate();};
  document.getElementById('assign').innerHTML=streams.map(s=>'<option>'+s.slug+'</option>').join('');
  buildSchema();
  loadTemplate();
  dirty=false; const st=document.getElementById('status'); st.textContent='Tudo salvo'; st.className='st';
}

function loadTemplate(){
  const base=JSON.parse(JSON.stringify(S.__base||S));
  S=templatesApplied(base,tplName); S.__base=base;
  buildForm(); refreshPreview();
}

function templatesApplied(cfg,name){
  const t=(cfg.templates||{})[name]||{};
  const out=JSON.parse(JSON.stringify(cfg));
  for(const k of ['render','branding']) out[k]={...(out[k]||{}), ...((t[k])||{})};
  return out;
}

async function saveAll(){
  const payload=JSON.parse(JSON.stringify(S)); delete payload.__base;
  const r=await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  if(r.ok){ dirty=false; const st=document.getElementById('status'); st.textContent='Salvo · vale no próximo ciclo'; st.className='st'; toast('Configuração salva'); }
  else { toast('Erro ao salvar'); }
}

async function reloadConfig(){ await load(); toast('Alterações descartadas'); }

async function saveAsTemplate(){
  const name=prompt('Nome do template', tplName==='default'?'canal':'novo');
  if(!name) return;
  const body={render:{},branding:{}};
  ['mode','fps','crf','preset','blur_sigma','karaoke_size','karaoke_words','karaoke_margin_v','hook_size','hook_caption','burn_subs','pip_scale','pip_position','pip_offset_y'].forEach(k=>{ if(g('render.'+k)!==undefined) body.render[k]=g('render.'+k); });
  ['handle','cta','accent','logo','logo_position','logo_width','handle_offset','cta_offset'].forEach(k=>{ if(g('branding.'+k)!==undefined) body.branding[k]=g('branding.'+k); });
  const r=await fetch('/api/templates/'+encodeURIComponent(name),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  toast(r.ok?('Template "'+name+'" salvo'):'Erro ao salvar template');
  await load();
}

async function delTemplate(){
  if(tplName==='default'){toast('O template default não pode ser apagado');return;}
  if(!confirm('Apagar o template '+tplName+'?')) return;
  await fetch('/api/templates/'+encodeURIComponent(tplName),{method:'DELETE'});
  tplName='default'; await load();
}

async function newTemplate(){
  const name=prompt('Nome do novo template');
  if(!name) return;
  await fetch('/api/templates/'+encodeURIComponent(name),{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  tplName=name; await load();
}

async function applyTemplate(){
  const slug=document.getElementById('assign').value;
  if(!slug) return;
  const r=await fetch('/api/streams/'+encodeURIComponent(slug)+'/template',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({template:tplName==='default'?null:tplName})});
  toast(r.ok?('Aplicado em '+slug):'Erro ao aplicar');
}

async function runPurge(dry){
  if(!dry && !confirm('Apagar agora os arquivos fora da retenção?')) return;
  const r=await fetch('/api/purge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dry_run:dry})});
  const j=await r.json().catch(()=>({}));
  const el=document.getElementById('purgeout');
  if(j.error){el.textContent='erro: '+j.error;return;}
  el.textContent=(dry?'Sairia: ':'Saiu: ')+(j.clips_removed||0)+' clipes · '+(j.orphans_removed||0)+' órfãos · '+(((j.bytes_freed||0)/1e6).toFixed(1))+' MB';
}

function toast(msg){const t=document.getElementById('toast');t.textContent=msg;t.classList.add('on');setTimeout(()=>t.classList.remove('on'),2600);}
window.addEventListener('beforeunload',(e)=>{ if(dirty){ e.preventDefault(); e.returnValue=''; } });
load();
</script></body></html>"""
