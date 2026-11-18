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
.layer{position:absolute;inset:0;pointer-events:none}
.handle{position:absolute;transform:translate(-50%,-50%);border:1px dashed rgba(140,180,255,.55);background:rgba(110,168,255,.10);border-radius:4px;pointer-events:auto;cursor:move;display:grid;place-items:center}
.handle span{font-size:9px;color:#cfe1ff;background:rgba(0,0,0,.55);padding:1px 4px;border-radius:3px;pointer-events:none;white-space:nowrap}
.handle.drag{border-color:var(--acc);background:rgba(255,212,0,.14)}
.mini{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px}
.mini .t{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--faint);margin-bottom:8px}
.mini .row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.mini .row.full{grid-template-columns:1fr}
.mini .row>*{min-width:0}

.tpl-row{display:grid;grid-template-columns:150px 80px 80px 90px 64px;gap:8px;align-items:center;padding:6px 0}
.tpl-head{font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:var(--faint);border-bottom:1px solid var(--line);padding-bottom:6px;margin-bottom:4px}
.tpl-head div{text-align:center}
.tpl-name{font-size:12.5px;color:var(--fg)}
.tpl-row .inp{height:30px;font-size:12px;text-align:center}
.tpl-row .inp.c{padding:2px}
.sub{margin-top:18px;padding-top:14px;border-top:1px solid var(--line)}
.sub-t{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--faint);margin-bottom:8px}
.pool{display:flex;flex-wrap:wrap;gap:8px}
.thumb{width:64px;height:64px;padding:0;border-radius:8px;border:2px solid var(--line);background:#000;overflow:hidden;cursor:pointer}
.thumb img{width:100%;height:100%;object-fit:cover;display:block}
.thumb.on{border-color:var(--acc)}
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
    <div class="pv" id="pvwrap"><img id="preview" alt=""><div class="layer" id="layer"></div><span class="ph" id="ph">Gerando preview…</span></div>
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
     {p:'publish.min_gap_minutes',l:'intervalo entre posts',h:'espalha os vídeos no dia; 0 = publica tudo junto',u:'min',t:'num',min:0,max:1440},
     {p:'publish.max_attempts',l:'tentativas em caso de erro',t:'num',min:1,max:20},
     {p:'publish.retry_minutes',l:'espera entre tentativas',u:'min',t:'num',min:1,max:240},
     {p:'publish.max_per_day',l:'máximo de uploads por dia',h:'0 = sem limite próprio; o YouTube também impõe um teto por canal',t:'num',min:0,max:100},
     {p:'publish.category_id',l:'categoria do YouTube',h:'20 = Gaming',t:'text'},
     {p:'publish.description_footer',l:'rodapé da descrição',t:'text'}]);

  sec('manutencao','Manutenção','o que apagar e quando; clipe não publicado nunca sai',
    [{p:'maintenance.enabled',l:'limpeza automática',t:'bool'},
     {p:'maintenance.clip_retention_days',l:'apagar clipes publicados após',u:'dias',t:'num',min:1,max:3650},
     {p:'maintenance.keep_unpublished_days',l:'não publicado: guardar por',h:'0 = nunca apaga',t:'num',min:0,max:3650},
     {p:'maintenance.db_retention_days',l:'apagar log e custo após',u:'dias',t:'num',min:7,max:3650},
     {p:'maintenance.run_every_hours',l:'rodar a cada',u:'h',t:'num',min:1,max:168}]);

  sec('template','Template do vídeo','Posição dos textos, fundo e arte do canal', []);

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

const TABS=[['geral','Captura'],['momento','Detecção'],['juiz','Classificador'],['video','Vídeo'],['marca','Marca'],['template','Template'],['publicacao','Publicação'],['manutencao','Manutenção'],['transcricao','Transcrição']];
let curTab='geral';

function tabOf(id){
  if(id==='captura') return 'geral';
  if(id==='momento') return 'momento';
  if(id==='juiz') return 'juiz';
  if(id==='video') return 'video';
  if(id==='marca') return 'marca';
  if(id==='template') return 'template';
  if(id==='publicacao') return 'publicacao';
  if(id==='manutencao') return 'manutencao';
  return 'transcricao';
}

function el(p,size,color){
  const L=((S.branding||{}).layout||{})[p]||{};
  return {x:L.x===undefined?540:L.x, y:L.y===undefined?200:L.y, size:L.size===undefined?size:L.size, color:L.color===undefined?color:L.color};
}

function swInput(key,checked,label){
  return '<label class="sw"><input type="checkbox" data-tpl="'+key+'" '+(checked?'checked':'')+'><span></span></label>';
}

function templateHtml(){
  const b=S.branding||{};
  const lay=b.layout||{};
  const bg=b.background||{mode:'blur',images:[]};
  const art=b.art||{image:'',opacity:1};
  const blocos=[['hook','Gancho',92,'0xFFD400'],['handle','@ do canal',46,'0xFFFFFF'],['cta','CTA do rodapé',40,'0xFFD400'],['extra','Texto extra',38,'0xFFFFFF']];

  const campos = blocos.map(([k,label,size,color])=>{
    const e=el(k,size,color);
    return '<div class="tpl-row"><div class="tpl-name">'+label+'</div>'+
      '<input class="inp" type="number" data-tpl="'+k+'.x" value="'+e.x+'" title="X">'+
      '<input class="inp" type="number" data-tpl="'+k+'.y" value="'+e.y+'" title="Y">'+
      '<input class="inp" type="number" data-tpl="'+k+'.size" value="'+e.size+'" title="tamanho">'+
      '<input class="inp c" type="color" data-tpl="'+k+'.color" value="'+(typeof numToHex==='function'?numToHex(e.color):'#FFFFFF')+'">'+
    '</div>';
  }).join('');

  const extraOn = !!((lay.extra||{}).enabled);
  const extraTxt = (lay.extra||{}).text||'';

  const assets = window.ASSETS||{bg:[],art:[],logo:[]};
  const pool = (bg.images||[]);
  const thumbs = (assets.bg||[]).map(a=>{
    const on = pool.includes(a.path);
    return '<button type="button" class="thumb'+(on?' on':'')+'" data-pick="'+a.path+'" title="'+a.name+'">'+
      '<img src="/media/asset?p='+encodeURIComponent(a.path)+'" alt=""></button>';
  }).join('') || '<div class="hint">nenhuma imagem enviada</div>';

  return ''+
  '<section class="card" id="template"><header><h2>Template do vídeo</h2><p>Posição dos textos, fundo e arte do canal</p></header><div class="body">'+
    '<div class="hint" style="margin:2px 0 10px">Arraste os elementos direto no preview. Snap automático no centro. Os números abaixo também funcionam.</div>'+
    '<div class="tpl-head tpl-row"><div class="tpl-name">elemento</div><div>X</div><div>Y</div><div>tamanho</div><div>cor</div></div>'+
    campos+
    '<div class="frow"><div class="lab"><label>Texto extra</label><span class="hint">use variáveis: {streamer} · {handle} · {date}</span></div>'+
      '<input class="inp" type="text" data-tpl="extra.text" value="'+String(extraTxt).replace(/"/g,'&quot;')+'"></div>'+
    '<div class="frow"><div class="lab"><label>Mostrar texto extra</label><span class="hint">linha livre acima do @</span></div>'+
      '<label class="sw"><input type="checkbox" data-tpl="extra.enabled" '+(extraOn?'checked':'')+'><span></span></label></div>'+

    '<div class="sub"><div class="sub-t">Fundo</div>'+
      '<div class="frow"><div class="lab"><label>Modo</label><span class="hint">imagem usa uma do pool; sorteia por clipe</span></div>'+
        '<select class="inp" data-tpl="background.mode">'+
          '<option value="blur"'+(bg.mode!=='image'?' selected':'')+'>Desfoque do vídeo</option>'+
          '<option value="image"'+(bg.mode==='image'?' selected':'')+'>Imagem do pool</option>'+
        '</select></div>'+
      '<div class="pool">'+thumbs+'</div>'+
      '<div class="row" style="margin-top:10px"><label class="btn" style="cursor:pointer">enviar imagem<input type="file" accept="image/*" hidden data-upload="bg"></label>'+
      '<span class="hint" style="align-self:center">'+(pool.length)+' selecionada(s)</span></div>'+
    '</div>'+

    '<div class="sub"><div class="sub-t">Arte do canal</div>'+
      '<div class="frow"><div class="lab"><label>Imagem sobreposta</label><span class="hint">PNG com transparência; fica por cima do vídeo</span></div>'+
        '<label class="btn" style="cursor:pointer">enviar arte<input type="file" accept="image/*" hidden data-upload="art"></label></div>'+
      '<div class="frow"><div class="lab"><label>Opacidade</label></div>'+
        '<input class="inp" type="number" step="0.05" min="0" max="1" data-tpl="art.opacity" value="'+art.opacity+'"></div>'+
      '<div class="frow"><div class="lab"><label>Arte atual</label></div><div class="hint" id="artname">'+(art.image? String(art.image).split('/').pop():'nenhuma')+'</div></div>'+
    '</div>'+
  '</div></section>';
}

function buildForm(){
  document.getElementById('nav').innerHTML = '<div class="grp">Abas</div>' +
    TABS.map(([id,label])=>'<a href="#" data-tab="'+id+'" class="'+(curTab===id?'on':'')+'">'+label+'</a>').join('');

  const sectionHtml = F.map(f=>{
    if(f.id==='template') return templateHtml();
    return '<section class="card" id="'+f.id+'"><header><h2>'+f.title+'</h2><p>'+f.hint+'</p></header>'+
      '<div class="body">'+f.items.map(it=>
        '<div class="frow"><div class="lab"><label>'+it.l+'</label>'+(it.h?'<span class="hint">'+it.h+'</span>':'')+'</div>'+control(it)+'</div>'
      ).join('')+'</div></section>';
  }).join('');

  // garante a aba do template mesmo sem secao declarada
  const hasTemplate = F.some(f=>f.id==='template');
  document.getElementById('forms').innerHTML = sectionHtml + (hasTemplate?'':templateHtml());
  if(curTab==='template') setTimeout(renderHandles, 60);

  document.querySelectorAll('section.card').forEach(sec=>{
    sec.style.display = tabOf(sec.id)===curTab ? '' : 'none';
  });

  document.querySelectorAll('[data-tab]').forEach(a=>{
    a.onclick=(ev)=>{ ev.preventDefault(); curTab=a.dataset.tab; buildForm(); if(curTab==='template') refreshPreview(); };
  });

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

  document.querySelectorAll('[data-tpl]').forEach(el=>{
    const ev = el.type==='checkbox' ? 'change' : 'input';
    el.addEventListener(ev,()=>{
      const path=el.dataset.tpl;
      let v=el.value;
      if(el.type==='checkbox') v=el.checked;
      else if(el.type==='number') v=Number(v);
      else if(el.type==='color') v=hexToNum(v);
      const [a,b]=path.split('.');
      if(a==='extra'||a==='hook'||a==='handle'||a==='cta'){
        S.branding.layout=S.branding.layout||{};
        S.branding.layout[a]=S.branding.layout[a]||{};
        S.branding.layout[a][b]=v;
      } else if(a==='background'){
        S.branding.background=S.branding.background||{mode:'blur',images:[]};
        S.branding.background[b]=v;
      } else if(a==='art'){
        S.branding.art=S.branding.art||{image:'',opacity:1};
        S.branding.art[b]=v;
      }
      markDirty(); schedulePreview();
    });
  });

  document.querySelectorAll('[data-pick]').forEach(btn=>{
    btn.onclick=()=>{
      S.branding.background=S.branding.background||{mode:'blur',images:[]};
      const imgs=new Set(S.branding.background.images||[]);
      const p=btn.dataset.pick;
      if(imgs.has(p)) imgs.delete(p); else imgs.add(p);
      S.branding.background.images=[...imgs];
      S.branding.background.mode='image';
      buildForm(); markDirty(); schedulePreview();
    };
  });

  document.querySelectorAll('[data-upload]').forEach(input=>{
    input.onchange=async ()=>{
      const file=input.files&&input.files[0]; if(!file) return;
      const kind=input.dataset.upload;
      const b64=await new Promise(res=>{const fr=new FileReader();fr.onload=()=>res(fr.result);fr.readAsDataURL(file);});
      const r=await fetch('/api/upload',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,name:file.name,data:b64})});
      const j=await r.json().catch(()=>({}));
      if(!j.ok){ toast('erro no upload: '+(j.error||r.status)); return; }
      if(kind==='art'){ S.branding.art=S.branding.art||{image:'',opacity:1}; S.branding.art.image=j.path; }
      if(kind==='bg'){ S.branding.background=S.branding.background||{mode:'image',images:[]}; S.branding.background.mode='image'; S.branding.background.images=[...(S.branding.background.images||[]), j.path]; }
      await loadAssets(); buildForm(); markDirty(); schedulePreview(); toast('imagem enviada');
    };
  });
}

async function loadAssets(){ try{ window.ASSETS=await (await fetch('/api/assets')).json(); }catch(e){ window.ASSETS={bg:[],art:[],logo:[]}; } }

function markDirty(){ dirty=true; const st=document.getElementById('status'); st.textContent='Alterações não salvas'; st.className='st dirty'; }

let tmr=null;
function schedulePreview(){clearTimeout(tmr);tmr=setTimeout(refreshPreview,450);}

async function refreshPreview(){
  const img=document.getElementById('preview'), ph=document.getElementById('ph');
  const body={
    template:tplName,
    hook:document.getElementById('hook').value,
    layout:document.getElementById('layout').value,
    render:{...(S.render||{})},
    branding:{...(S.branding||{})},
    variables:{streamer:document.getElementById('assign').value||'canal', date:new Date().toLocaleDateString('pt-BR').slice(0,5)}
  };
  try{
    const r=await fetch('/api/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r.ok){ph.textContent='Preview indisponível';ph.style.display='block';return;}
    img.src=URL.createObjectURL(await r.blob());
    ph.style.display='none';
    img.onload=()=>renderHandles();
  }catch(e){ ph.textContent='Preview falhou'; ph.style.display='block'; }
}

const DRAGGABLE=[['hook','Gancho'],['handle','@ do canal'],['cta','CTA'],['extra','Texto extra']];

function layoutOf(k){
  S.branding=S.branding||{};
  S.branding.layout=S.branding.layout||{};
  S.branding.layout[k]=S.branding.layout[k]||{};
  return S.branding.layout[k];
}

function renderHandles(){
  const layer=document.getElementById('layer');
  if(!layer) return;
  layer.innerHTML='';
  const lay=(S.branding||{}).layout||{};
  for(const [k,label] of DRAGGABLE){
    const e=lay[k]||{};
    if(k==='extra' && !e.enabled) continue;
    const size=Number(e.size||40);
    const w=Math.max(size*4.2, size*(label.length*0.55));
    const h=size*1.7;
    const box=document.createElement('div');
    box.className='handle';
    box.dataset.k=k;
    box.style.left=((e.x===undefined?540:e.x)/1080*100)+'%';
    box.style.top=((e.y===undefined?960:e.y)/1920*100)+'%';
    box.style.width=(w/1080*100)+'%';
    box.style.height=(h/1920*100)+'%';
    box.innerHTML='<span>'+label+'</span>';
    box.addEventListener('pointerdown',startDrag);
    layer.appendChild(box);
  }
}

let dragging=null;

function startDrag(ev){
  ev.preventDefault();
  const box=ev.currentTarget;
  const k=box.dataset.k;
  const wrap=document.getElementById('pvwrap');
  const rect=wrap.getBoundingClientRect();
  dragging={k, box, rect};
  box.classList.add('drag');
  box.setPointerCapture(ev.pointerId);
  box.addEventListener('pointermove',onDrag);
  box.addEventListener('pointerup',endDrag);
  box.addEventListener('pointercancel',endDrag);
}

function onDrag(ev){
  if(!dragging) return;
  const {k, box, rect}=dragging;
  let x=(ev.clientX-rect.left)/rect.width*1080;
  let y=(ev.clientY-rect.top)/rect.height*1920;
  // snap: centro e bordas
  if(Math.abs(x-540)<16) x=540;
  if(Math.abs(y-960)<16) y=960;
  x=Math.max(40, Math.min(1040, Math.round(x/2)*2));
  y=Math.max(40, Math.min(1880, Math.round(y/2)*2));

  const e=layoutOf(k);
  e.x=x; e.y=y;
  box.style.left=(x/1080*100)+'%';
  box.style.top=(y/1920*100)+'%';

  const ix=document.querySelector('[data-tpl="'+k+'.x"]');
  const iy=document.querySelector('[data-tpl="'+k+'.y"]');
  if(ix) ix.value=x;
  if(iy) iy.value=y;
  markDirty();
}

function endDrag(ev){
  if(!dragging) return;
  dragging.box.classList.remove('drag');
  dragging=null;
  refreshPreview();
}

async function load(){
  await loadAssets();
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
  const j=await r.json().catch(()=>({}));
  if(r.ok){ dirty=false; const st=document.getElementById('status'); st.textContent='Salvo · vale no próximo ciclo'; st.className='st'; toast('Configuração salva'); }
  else { toast('Erro ao salvar: '+(j.error||('HTTP '+r.status))); }
}

async function reloadConfig(){ await load(); toast('Alterações descartadas'); }

async function saveAsTemplate(){
  const name=prompt('Nome do template', tplName==='default'?'canal':'novo');
  if(!name) return;
  const body={render:{},branding:{}};
  ['mode','fps','crf','preset','blur_sigma','karaoke_size','karaoke_words','karaoke_margin_v','hook_size','hook_caption','burn_subs','pip_scale','pip_position','pip_offset_y'].forEach(k=>{ if(g('render.'+k)!==undefined) body.render[k]=g('render.'+k); });
  ['handle','cta','accent','logo','logo_position','logo_width','handle_offset','cta_offset'].forEach(k=>{ if(g('branding.'+k)!==undefined) body.branding[k]=g('branding.'+k); });
  const r=await fetch('/api/templates/'+encodeURIComponent(name),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const j=await r.json().catch(()=>({}));
  toast(r.ok?('Template "'+name+'" salvo'):('Erro ao salvar template: '+(j.error||r.status)));
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
