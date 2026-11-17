"""Pagina de configuracoes + builder de template."""

SETTINGS_PAGE = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>cortai — configurações</title>
<style>
:root{--bg:#0b0c0f;--card:#14161b;--line:#23262e;--fg:#e8eaed;--dim:#8b929e;--acc:#ffd400;--ok:#3ddc84;--bad:#ff5c5c}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:13px/1.5 ui-sans-serif,system-ui,Segoe UI,Roboto,sans-serif}
header{position:sticky;top:0;z-index:5;display:flex;gap:14px;align-items:center;padding:12px 20px;background:rgba(11,12,15,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
header h1{margin:0;font-size:14px;font-weight:600}
header h1 b{color:var(--acc)}
header a{color:var(--dim);text-decoration:none;font-size:12px}
header a:hover{color:var(--fg)}
.spacer{flex:1}
button{font-family:inherit}
.btn{padding:8px 16px;border-radius:9px;border:1px solid #2f3540;background:#1b1e25;color:var(--fg);cursor:pointer;font-size:12px;font-weight:600}
.btn:hover{border-color:#4a515f}
.btn.primary{background:#22301f;border-color:rgba(61,220,132,.45);color:var(--ok)}
.btn.danger{color:var(--bad);border-color:rgba(255,92,92,.4)}
main{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:20px;padding:18px 20px 80px;align-items:start}
@media(max-width:1080px){main{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:14px;overflow:hidden}
.card h2{margin:0;padding:11px 14px;font-size:11px;text-transform:uppercase;letter-spacing:.11em;color:var(--dim);border-bottom:1px solid var(--line);font-weight:600}
.card .body{padding:14px;display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px}
.field{display:grid;gap:5px}
.field label{font-size:11px;color:var(--dim)}
.field input,.field select{width:100%;padding:8px 10px;border-radius:8px;border:1px solid var(--line);background:#0f1116;color:var(--fg);font-size:12px}
.field input:focus,.field select:focus{outline:none;border-color:#3a3f4b}
.field input[type=color]{padding:2px;height:34px}
aside{position:sticky;top:64px;display:grid;gap:12px}
.pv{background:#000;border:1px solid var(--line);border-radius:12px;overflow:hidden;aspect-ratio:9/16;display:grid;place-items:center}
.pv img{width:100%;height:100%;object-fit:contain;display:block}
.pv .ph{color:#3a3f4b;font-size:12px}
.row{display:flex;gap:8px}
.row > *{flex:1}
#toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#1b1e25;border:1px solid var(--line);padding:9px 16px;border-radius:9px;font-size:12px;opacity:0;transition:.2s;pointer-events:none}
#toast.on{opacity:1}
.hint{color:var(--dim);font-size:11px;padding:0 14px 12px}
</style></head>
<body>
<header>
  <h1>cortai <b>·</b> configurações</h1>
  <a href="/">← painel</a>
  <span class="spacer"></span>
  <select id="tpl" class="btn" title="template"></select>
  <button class="btn" onclick="newTemplate()">novo</button>
  <button class="btn danger" onclick="delTemplate()">excluir</button>
  <button class="btn primary" onclick="saveAll()">salvar</button>
</header>
<main>
  <div id="forms"></div>
  <aside>
    <div class="pv"><img id="preview" alt=""><span class="ph" id="ph">gerando preview…</span></div>
    <div class="card"><div class="body">
      <div class="field"><label>gancho do exemplo</label><input id="hook" value="NAO E POSSIVEL"></div>
      <div class="field"><label>layout</label>
        <select id="layout"><option value="pip">pip</option><option value="face">face</option><option value="game">game</option></select>
      </div>
      <div class="field"><label>aplicar template na live</label><select id="assign"></select></div>
    </div>
    <div class="row" style="padding:0 14px 14px">
      <button class="btn" onclick="applyTemplate()">aplicar</button>
      <button class="btn" onclick="saveAsTemplate()">salvar como template</button>
    </div></div>
    <div class="card"><h2>limpeza de disco</h2>
      <div class="row" style="padding:0 14px 10px">
        <button class="btn" onclick="runPurge(true)">simular</button>
        <button class="btn danger" onclick="runPurge(false)">limpar agora</button>
      </div>
      <div class="hint" id="purgeout">respeita a retenção acima</div>
    </div>
  </aside>
</main>
<div id="toast"></div>
<script>
let S=null, streams=[], tplName='default';
const F=[];
function sec(title, items, hint){F.push({title, items, hint});}

function g(path){return path.split('.').reduce((o,k)=>(o==null?undefined:o[k]),S);}
function s(path,v){const ks=path.split('.');let o=S;for(let i=0;i<ks.length-1;i++){o[ks[i]]=o[ks[i]]||{};o=o[ks[i]];}o[ks[ks.length-1]]=v;}

function hexToNum(h){return '0x'+String(h||'#FFD400').replace('#','').toUpperCase();}
function numToHex(v){return '#'+String(v||'0xFFD400').replace(/^0x/i,'').slice(-6);}

function buildForm(){
  F.length=0;
  sec('Captura', [
    {p:'live.window_s',l:'janela de análise (s)',t:'num',min:30,max:180},
    {p:'live.cycle_s',l:'ciclo (s)',t:'num',min:5,max:60},
    {p:'live.min_buffer_s',l:'buffer mínimo (s)',t:'num',min:20,max:300},
    {p:'live.buffer_seconds',l:'buffer total (s)',t:'num',min:120,max:1800},
  ]);
  sec('Detecção de momento', [
    {p:'moments.peak_z',l:'sensibilidade (peak_z)',t:'num',step:0.1,min:0.3,max:4},
    {p:'moments.min_sep_s',l:'separação mínima (s)',t:'num',min:5,max:300},
    {p:'moments.context_pre_s',l:'contexto antes (s)',t:'num',min:2,max:60},
    {p:'moments.context_post_s',l:'contexto depois (s)',t:'num',min:5,max:90},
    {p:'moments.min_clip_s',l:'duração mínima (s)',t:'num',min:5,max:60},
    {p:'moments.max_clip_s',l:'duração máxima (s)',t:'num',min:10,max:90},
  ]);
  sec('Classificador', [
    {p:'classify.min_score',l:'nota mínima p/ aprovar',t:'num',step:0.5,min:0,max:10},
    {p:'classify.frames',l:'frames por análise',t:'num',min:1,max:10},
    {p:'classify.jev.min_score',l:'gate Jev: nota mínima',t:'num',step:0.5,min:0,max:10},
    {p:'classify.jev.min_event',l:'gate Jev: evento mínimo',t:'num',step:0.05,min:0,max:1},
  ], 'gate Jev filtra barato; o LLM só escreve a copy dos aprovados');
  sec('Vídeo', [
    {p:'render.mode',l:'enquadramento',t:'sel',opts:[['pad_blur','pad_blur (barras)'],['crop','crop (segue ação)']]},
    {p:'render.fps',l:'fps de saída',t:'num',min:15,max:60},
    {p:'render.crf',l:'qualidade (crf, menor=melhor)',t:'num',min:14,max:32},
    {p:'render.preset',l:'preset x264',t:'sel',opts:[['ultrafast','ultrafast'],['veryfast','veryfast'],['fast','fast'],['medium','medium']]},
    {p:'render.blur_sigma',l:'desfoque do fundo',t:'num',min:0,max:60},
    {p:'render.karaoke_size',l:'legenda: tamanho',t:'num',min:40,max:140},
    {p:'render.karaoke_words',l:'legenda: palavras por vez',t:'num',min:1,max:6},
    {p:'render.karaoke_margin_v',l:'legenda: altura do rodapé',t:'num',min:40,max:700},
    {p:'render.hook_size',l:'gancho: tamanho',t:'num',min:40,max:160},
    {p:'render.hook_caption',l:'mostrar gancho',t:'bool'},
    {p:'render.burn_subs',l:'queimar legenda',t:'bool'},
  ]);
  sec('Marca', [
    {p:'branding.handle',l:'@ do canal',t:'text'},
    {p:'branding.cta',l:'chamada no rodapé',t:'text'},
    {p:'branding.accent',l:'cor de destaque',t:'color'},
    {p:'branding.logo',l:'logo (caminho)',t:'text'},
    {p:'branding.logo_position',l:'posição do logo',t:'sel',opts:[['tl','topo esq'],['tr','topo dir'],['bl','baixo esq'],['br','baixo dir']]},
    {p:'branding.logo_width',l:'largura do logo',t:'num',min:60,max:600},
    {p:'branding.handle_offset',l:'distância do @',t:'num',min:0,max:800},
    {p:'branding.cta_offset',l:'distância do CTA',t:'num',min:0,max:800},
    {p:'render.pip_scale',l:'facecam: tamanho no pip',t:'num',step:0.01,min:0.15,max:0.6},
    {p:'render.pip_position',l:'facecam: canto',t:'sel',opts:[['tr','topo dir'],['tl','topo esq'],['br','baixo dir'],['bl','baixo esq']]},
    {p:'render.pip_offset_y',l:'facecam: altura',t:'num',min:0,max:1200},
  ]);
  sec('Publicação', [
    {p:'publish.auto',l:'publicar sozinho',t:'bool'},
    {p:'publish.auto_min_score',l:'nota mínima p/ publicar (0–10)',t:'num',step:0.5,min:0,max:10},
    {p:'publish.privacy',l:'privacidade',t:'sel',opts:[['unlisted','não listado'],['public','público'],['private','privado']]},
    {p:'publish.schedule_hours',l:'horários de postagem (ex: 19,20 — vazio = na hora)',t:'list'},
    {p:'publish.max_attempts',l:'tentativas em caso de erro',t:'num',min:1,max:20},
    {p:'publish.retry_minutes',l:'espera entre tentativas (min)',t:'num',min:1,max:240},
    {p:'publish.category_id',l:'categoria YouTube',t:'text'},
    {p:'publish.description_footer',l:'rodapé da descrição',t:'text'},
  ], 'nota é de 0 a 10: 8.0 publica só clipe nota 8 pra cima');
  sec('Manutenção', [
    {p:'maintenance.enabled',l:'limpeza automática',t:'bool'},
    {p:'maintenance.clip_retention_days',l:'apagar clipes com mais de (dias)',t:'num',min:1,max:3650},
    {p:'maintenance.keep_unpublished_days',l:'não publicado: guardar por (dias, 0 = sempre)',t:'num',min:0,max:3650},
    {p:'maintenance.db_retention_days',l:'apagar log/custo com mais de (dias)',t:'num',min:7,max:3650},
    {p:'maintenance.run_every_hours',l:'rodar a cada (horas)',t:'num',min:1,max:168},
  ], 'só clipe publicado é apagado; não publicado fica guardado');

  sec('Transcrição', [
    {p:'asr.language',l:'idioma',t:'text'},
    {p:'asr.keyterms',l:'termos (separados por vírgula)',t:'list'},
  ]);

  const host=document.getElementById('forms');
  host.innerHTML=F.map((f,fi)=>(
    '<div class="card"><h2>'+f.title+'</h2><div class="body">'+
    f.items.map(it=>fieldHtml(it)).join('')+
    '</div>'+(f.hint?'<div class="hint">'+f.hint+'</div>':'')+'</div>'
  )).join('');
  host.querySelectorAll('[data-p]').forEach(el=>{
    el.addEventListener('input',()=>{
      const p=el.dataset.p, t=el.dataset.t;
      let v=el.value;
      if(t==='num') v=Number(v);
      if(t==='bool') v=el.checked;
      if(t==='color') v=hexToNum(v);
      if(t==='list') v=String(v).split(',').map(x=>x.trim()).filter(Boolean);
      s(p,v); schedulePreview();
    });
  });
}

function fieldHtml(it){
  const p=it.p, t=it.t||'text', v=g(p);
  let inner='';
  if(t==='bool') inner='<input type="checkbox" data-p="'+p+'" data-t="bool" '+(v?'checked':'')+'>';
  else if(t==='sel') inner='<select data-p="'+p+'" data-t="sel">'+it.opts.map(o=>'<option value="'+o[0]+'"'+(String(v)===o[0]?' selected':'')+'>'+o[1]+'</option>').join('')+'</select>';
  else if(t==='color') inner='<input type="color" data-p="'+p+'" data-t="color" value="'+numToHex(v)+'">';
  else if(t==='num') inner='<input type="number" data-p="'+p+'" data-t="num" value="'+(v==null?'':v)+'" '+(it.min!=null?'min="'+it.min+'" ':'')+(it.max!=null?'max="'+it.max+'" ':'')+(it.step?'step="'+it.step+'"':'')+'>';
  else if(t==='list') inner='<input type="text" data-p="'+p+'" data-t="list" value="'+((v||[]).join(', '))+'">';
  else inner='<input type="text" data-p="'+p+'" data-t="text" value="'+(v==null?'':String(v).replace(/"/g,'&quot;'))+'">';
  return '<div class="field"><label>'+it.l+'</label>'+inner+'</div>';
}

let tmr=null;
function schedulePreview(){clearTimeout(tmr);tmr=setTimeout(refreshPreview,450);}

async function refreshPreview(){
  const img=document.getElementById('preview'), ph=document.getElementById('ph');
  const body={
    template:tplName,
    hook:document.getElementById('hook').value,
    layout:document.getElementById('layout').value,
    render:{}, branding:{}
  };
  ['mode','fps','crf','preset','blur_sigma','karaoke_size','karaoke_words','karaoke_margin_v','hook_size','hook_caption','burn_subs','pip_scale','pip_position','pip_offset_y'].forEach(k=>{ if(g('render.'+k)!==undefined) body.render[k]=g('render.'+k); });
  ['handle','cta','accent','logo','logo_position','logo_width','handle_offset','cta_offset'].forEach(k=>{ if(g('branding.'+k)!==undefined) body.branding[k]=g('branding.'+k); });
  try{
    const r=await fetch('/api/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r.ok){ph.textContent='preview indisponível';return;}
    const blob=await r.blob();
    img.src=URL.createObjectURL(blob); img.style.display='block'; ph.style.display='none';
  }catch(e){ ph.textContent='preview falhou'; }
}

async function load(){
  S=(await (await fetch('/api/config')).json());
  streams=(await (await fetch('/api/state')).json()).streams||[];
  const tpls=Object.keys(S.templates||{default:{}});
  const sel=document.getElementById('tpl');
  sel.innerHTML=tpls.map(t=>'<option>'+t+'</option>').join('');
  sel.value=tpls.includes(tplName)?tplName:tpls[0];
  tplName=sel.value;
  sel.onchange=()=>{tplName=sel.value;loadTemplate();};
  const as=document.getElementById('assign');
  as.innerHTML=streams.map(s=>'<option>'+s.slug+'</option>').join('');
  loadTemplate();
}

function loadTemplate(){
  // aplica o template sobre o config base na copia em memoria
  const base=JSON.parse(JSON.stringify(S.__base||S));
  S=templatesApplied(base,tplName); S.__base=base;
  buildForm(); refreshPreview();
}

function templatesApplied(cfg,name){
  const t=(cfg.templates||{})[name]||{};
  const out=JSON.parse(JSON.stringify(cfg));
  for(const k of ['render','branding']){ out[k]={...(out[k]||{}), ...((t[k])||{})}; }
  return out;
}

async function saveAll(){
  const payload=JSON.parse(JSON.stringify(S)); delete payload.__base;
  const r=await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  toast(r.ok?'salvo · vale no próximo ciclo':'erro ao salvar');
}

async function saveAsTemplate(){
  const name=prompt('nome do template', tplName==='default'?'canal':'novo');
  if(!name) return;
  const body={render:{},branding:{}};
  ['mode','fps','crf','preset','blur_sigma','karaoke_size','karaoke_words','karaoke_margin_v','hook_size','hook_caption','burn_subs','pip_scale','pip_position','pip_offset_y'].forEach(k=>{ if(g('render.'+k)!==undefined) body.render[k]=g('render.'+k); });
  ['handle','cta','accent','logo','logo_position','logo_width','handle_offset','cta_offset'].forEach(k=>{ if(g('branding.'+k)!==undefined) body.branding[k]=g('branding.'+k); });
  const r=await fetch('/api/templates/'+encodeURIComponent(name),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  toast(r.ok?('template "'+name+'" salvo'):'erro');
  await load();
}

async function delTemplate(){
  if(tplName==='default'){toast('o template default não pode ser apagado');return;}
  if(!confirm('apagar o template '+tplName+'?')) return;
  await fetch('/api/templates/'+encodeURIComponent(tplName),{method:'DELETE'});
  tplName='default'; await load();
}

async function newTemplate(){
  const name=prompt('nome do novo template');
  if(!name) return;
  await fetch('/api/templates/'+encodeURIComponent(name),{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
  tplName=name; await load();
}

async function applyTemplate(){
  const slug=document.getElementById('assign').value;
  if(!slug) return;
  const r=await fetch('/api/streams/'+encodeURIComponent(slug)+'/template',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({template:tplName==='default'?null:tplName})});
  toast(r.ok?('aplicado em '+slug):'erro');
}

async function runPurge(dry){
  if(!dry && !confirm('apagar agora os arquivos fora da retenção?')) return;
  const r=await fetch('/api/purge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dry_run:dry})});
  const j=await r.json().catch(()=>({}));
  const el=document.getElementById('purgeout');
  if(j.error){el.textContent='erro: '+j.error;return;}
  el.textContent=(dry?'sairia: ':'saiu: ')+(j.clips_removed||0)+' clipes · '+(j.orphans_removed||0)
    +' órfãos · '+(j.log_rows||0)+' logs · '+(((j.bytes_freed||0)/1e6).toFixed(1))+' MB';
}

function toast(msg){
  const t=document.getElementById('toast'); t.textContent=msg; t.classList.add('on');
  setTimeout(()=>t.classList.remove('on'),2600);
}
load();
</script></body></html>"""
