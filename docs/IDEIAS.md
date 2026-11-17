# Ideias pendentes

Anotado para depois. Nada aqui está implementado.

## 1. Loop de analytics (a mais importante)

**Problema:** o sistema decide por heurística e nunca descobre se acertou. A nota do
clipe é uma opinião do modelo, não uma medida de resultado.

**Ideia:** depois de publicar, ler as estatísticas do vídeo e gravar no banco.

```
clips.analytics = {"views": 1234, "likes": 45, "comments": 8,
                   "checked_at": ..., "first_24h_views": 800}
```

- Fonte: YouTube Data API `videos.list(part=statistics)` — custa **1 unidade**, dá
  `viewCount`, `likeCount`, `commentCount`. Suficiente para começar.
- Retenção e CTR de impressão exigem a **YouTube Analytics API** (outro escopo OAuth:
  `yt-analytics.readonly`). Vale depois do primeiro passo.
- Coleta: job diário nos primeiros 7 dias de cada vídeo (o pico de Shorts é nas
  primeiras 48h).

**O que isso destrava:**

1. Responder "quantos dos clipes aprovados dão view?" — hoje não sabemos.
2. Correlacionar `score` do classificador com `views`. Se clipe nota 8 rende o mesmo
   que nota 5, a nota não serve e o gate precisa ser refeito.
3. Ajustar `moments.peak_z` e `classify.min_score` com dado, não com intuição.
4. Ranking de layout: `pip` vs `face` vs `game` por views. Hoje é escolha do modelo
   sem nenhum retorno.

**Esboço de código:**

```python
# live/analytics.py
def collect(db, cfg, days=7):
    for clip in db.clips_with_youtube_id(max_age_days=days):
        stats = yt.video_stats(clip.youtube_id)   # videos.list, 1 unidade
        db.update_clip(clip.id, analytics=stats)
```

CLI: `lives.py analytics` (coleta) e `lives.py report` (tabela score × views).

## 2. Um token por canal

Hoje `work/youtube_token.json` é uma conta só. Quem roda vários canais precisa trocar
o arquivo na mão. Correção: token por template (`work/tokens/<template>.json`) e o
upload escolhe pelo template da live.

## 3. Instalador / updater

Amigos clonam o repo e fazem `git pull` na mão. Um `lives.py update` (git pull +
pip install + aviso de restart) economizaria suporte. Um pacote zip com ffmpeg
embutido seria o próximo nível.

## 4. Variação de gancho e título

Gerar 2–3 opções de gancho por clipe e sortear (ou testar A/B com dois uploads
não listados). Só faz sentido medir depois do item 1.

## 5. Fila com prioridade

Hoje a fila é FIFO. Se saírem 10 clipes de uma vez, todos publicam no mesmo horário —
o que pode canibalizar o alcance. Distribuir dentro da janela de `schedule_hours`,
um a cada N minutos.
