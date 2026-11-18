# cortai — cortes automáticos de live

Assiste N lives ao mesmo tempo, guarda os últimos minutos em disco, escuta o áudio,
transcreve, classifica o momento com LLM (vendo frames), corta em vertical com legenda
e publica no YouTube.

```bash
git clone https://github.com/hadagalberto/cortai.git
cd cortai
```

Precisa de **Python 3.10+**, **ffmpeg com libass** e uma chave do **OpenRouter**.
Passo a passo em [Instalação](#instalação).

## Como funciona

```
ㅤ
  stream (twitch/youtube)                         .----------------------.
        |                                         |  DADO PARA O POST    |
        v                                         |  .mp4 + .txt + .json |
  [streamlink resolve url]                        '----------+-----------'
        |                                                    ^
        v                                                    |
  [ffmpeg segmenta 6s] -> ring/ (buffer circular 10 min)     |
        |                                                    |
        v                                    keep + score>=7 |
  [janela deslizante de 60s]                                  |
        |                                                     |
        +--> [gate de áudio+chat]  peaks por z-score ----------+
                     |                                        ^
                     |  só o candidato (~10% do tempo)        |
                     v                                        |
        [ASR scribe-v2] -> texto + gate Jev -> [LLM vê 6 frames + texto]
                                                  OpenRouter
```

Só olha o trecho que passou do gate. É o que mantém o custo em ~US$1,80/dia em 5 lives
em vez de ~US$40.

## Instalação

### Opção A — Docker (recomendado para VPS)

```bash
cp .env.example .env          # preencha OPENROUTER_API_KEY
echo "PANEL_PASSWORD=troque-essa-senha" >> .env
docker compose build
docker compose up -d
```

Painel em `http://SEU_IP:8787`. `work/`, `out/`, `config.json` e `branding/` ficam
montados como volume — você edita na máquina, não dentro do container.

### Opção B — direto na máquina

Sem Docker. Quatro passos, uns 10 minutos na primeira vez.

#### 1. Python 3.10 ou mais novo

**Windows** — abra o PowerShell e rode:

```powershell
winget install Python.Python.3.12
```

Ou baixe em https://www.python.org/downloads/ — **marque a caixa "Add python.exe to
PATH"** na primeira tela. Sem isso o terminal não acha o comando depois.

**Ubuntu/Debian:**

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip
```

**macOS:** `brew install python@3.12`

Confira (feche e reabra o terminal antes):

```powershell
python --version      # no Linux/macOS pode ser python3 --version
```

#### 2. Ambiente virtual (não pule)

Isola as bibliotecas do projeto e evita conflito com o resto da máquina.

```powershell
cd caminho\do\lives
python -m venv .venv
.\.venv\Scripts\activate        # Windows PowerShell
```

```bash
python3 -m venv .venv && source .venv/bin/activate   # Linux/macOS
```

O terminal passa a mostrar `(.venv)` no começo da linha. **Toda vez que abrir um
terminal novo para usar o sistema, ative de novo.**

#### 3. Dependências

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

Leva 1–3 minutos. O que está sendo instalado:

| pacote | para quê |
|---|---|
| `numpy` | análise de áudio (FFT) |
| `requests` | chamadas de API |
| `yt-dlp`, `streamlink` | puxar a live |
| `chat-downloader` | chat do YouTube/Kick (Twitch usa IRC nativo) |
| `opencv-python-headless` | detectar a facecam |
| `google-api-python-client`, `google-auth-oauthlib` | publicar no YouTube |

#### 4. ffmpeg

O sistema **não funciona sem** — é ele que corta e monta o vídeo.

```powershell
winget install Gyan.FFmpeg        # Windows
```

```bash
sudo apt install -y ffmpeg        # Ubuntu/Debian
brew install ffmpeg               # macOS
```

Feche e reabra o terminal para o `ffmpeg` entrar no PATH.

#### 5. Conferir

```powershell
copy .env.example .env     # depois edite e ponha a OPENROUTER_API_KEY
python cortai.py doctor
```

Se aparecer tudo `[OK]`, está pronto. `doctor` diz exatamente o que falta.

### Se der erro

| mensagem | causa | solução |
|---|---|---|
| `python não é reconhecido` | não entrou no PATH | use `py` no Windows, ou reinstale marcando "Add to PATH" |
| `pip não é reconhecido` | idem | `python -m pip install ...` |
| `externally-managed-environment` (Linux) | Python do sistema protegido | crie o venv (passo 2) — não use `--break-system-packages` |
| `ffmpeg não encontrado` | instalou mas o terminal é antigo | feche e reabra; confira com `ffmpeg -version` |
| `ModuleNotFoundError` em algum pacote | venv não ativado | rode o passo 2 de novo |
| `error: Microsoft Visual C++ 14.0 required` | pip velho tentando compilar | `pip install --upgrade pip` e tente de novo |

## Onde fica cada configuração

| arquivo | o que guarda | você edita? |
|---|---|---|
| `.env` | chaves de API e senha do painel | sim |
| `config.json` | ajustes de captura, corte, vídeo, marca, publicação, templates | pelo painel ou à mão |
| `work/cortai.db` | lives cadastradas, clipes, custo, log | não |
| `work/panel_auth.json` | hash da senha, segredo da sessão | não |
| `work/youtube_token.json` | token do OAuth do YouTube | não |
| `work/<live>/facecam.json` | retângulo da facecam detectado | não |

**Por que não tudo no `.env`:** o `.env` é plano (`CHAVE=valor`) e o config é uma
árvore — templates por canal, listas, objetos aninhados. Além disso o painel **escreve**
no `config.json`; reescrever `.env` de dentro do app corromperia comentários e citações.

**Mas dá para controlar tudo pelo `.env`** se você quiser: qualquer caminho do config
aceita override por ambiente, com `CORTAI_` na frente e `__` separando os níveis.

```bash
CORTAI_RENDER__MODE=crop
CORTAI_RENDER__KARAOKE_SIZE=110
CORTAI_MOMENTS__PEAK_Z=1.7
CORTAI_PUBLISH__AUTO=true
CORTAI_PUBLISH__AUTO_MIN_SCORE=8
CORTAI_ASR__KEYTERMS=GTA,Trevor,Franklin
```

Booleano aceita `true/1/on/sim`, lista aceita `a,b,c`, número é convertido sozinho.
**O que estiver no ambiente vence o `config.json`** — inclusive mudanças salvas pelo
painel. Use isso para testes e valores fixos; deixe o resto no painel.

## Uso

```powershell
python cortai.py add --url https://www.twitch.tv/canal1
python cortai.py add --url https://www.youtube.com/watch?v=XXXX

python cortai.py run                 # roda todas as lives ativas
python cortai.py run --only canal1   # uma só
python cortai.py serve               # painel web em http://127.0.0.1:8787
python cortai.py clips               # lista o que saiu
python cortai.py selftest            # E2E offline, sem chave e sem internet
```

Saída: `out/YYYY-MM-DD/<slug>/<slug>_HHMMSS_<score>.mp4` + `.txt` (legenda) + `.json`
(metadados). Estado em `work/cortai.db` (SQLite).

## Senha e acesso pela rede (opcional)

Se é tudo na sua máquina, **pule esta seção** — o painel já abre em `127.0.0.1`
sem senha. Isto só serve se você quiser abrir de outro computador ou celular.

```powershell
python cortai.py passwd                  # define a senha do painel
python cortai.py serve --host 0.0.0.0    # expoe na rede local
```

Sem senha configurada, o painel **gera uma automaticamente** e imprime no console na
primeira vez que sobe exposto. Anote: não aparece de novo.

A sessão é um cookie `HttpOnly; SameSite=Strict`, assinado com HMAC, válido por 12h.
Senha com PBKDF2 (200k iterações). Cinco tentativas erradas bloqueiam o IP por 5 min.

Se um dia isso for para a internet (não só rede local), **TLS deixa de ser opcional**:
o servidor é HTTP puro e a senha iria em claro. Coloque nginx/caddy na frente com HTTPS
e rode com `--secure-cookie`.

## Painel

`python cortai.py serve` abre `http://127.0.0.1:8787` — só local, sem dependência nova.

- **preview ao vivo** por live: remux dos últimos ~6s do ring a cada 5s (~5s de atraso),
  sem re-encode. Consome CPU só enquanto a página está aberta.
- buffer, status no ar (frescor do último segmento) e facecam detectada.
- **candidatos** com score e a justificativa do LLM — é onde você vê o sistema pensando.
- **clipes** com thumbnail, layout usado e player.
- **👍/👎** em cada clipe. Cada voto vira linha rotulada no banco e o painel mostra a
  precisão (`👍 / (👍+👎)`). É como se mede se o gate está deixando passar ruído.

Se o painel mostrar candidatos com score baixo, isso é o classificador trabalhando:
ele está dizendo "isso não presta" e evitando lixo no seu canal.

### Cadastrar lives pelo painel

No topo da aba **lives** tem um campo de URL. Cole `https://www.twitch.tv/canal` e
clique em **adicionar** — o supervisor detecta e começa a capturar **sem reiniciar**.
O botão **parar** encerra aquela live na hora. O slug é derivado da URL.

O botão **remover** apaga o canal do painel junto com os clipes dele: registros no banco,
vídeos em `out/`, miniaturas e o buffer em `work/<slug>/`. O que já foi publicado no
YouTube continua no ar. A ação pede confirmação e não tem desfazer.

Os clipes ficam agrupados em **accordions por canal** — só o canal mais recente abre
por padrão, e o estado de aberto/fechado sobrevive às atualizações de 3s do painel.

## Publicar no YouTube

Seis passos, uma vez só. ~10 minutos.

### 1. Criar o projeto

1. https://console.cloud.google.com/projectcreate
2. Nome: `cortes` (qualquer coisa) → **Criar**
3. Confirme que o projeto novo está selecionado no topo da página

### 2. Ativar a API do YouTube

1. https://console.cloud.google.com/apis/library/youtube.googleapis.com
2. Clique em **Ativar**

Sem isso o upload responde `403` com "API não foi habilitada".

### 3. Tela de consentimento

1. https://console.cloud.google.com/apis/credentials/consent
2. Tipo de usuário: **Externo** → **Criar**
3. Preencha só o obrigatório (nome do app, seu e-mail de suporte, seu e-mail) e salve
4. Em **Usuários de teste**, clique em **Adicionar usuários** e ponha o e-mail da conta
   que vai postar. Sem isso a autorização falha com "acesso bloqueado".

### 4. Criar a credencial

1. https://console.cloud.google.com/apis/credentials
2. **Criar credenciais** → **ID do cliente OAuth**
3. Tipo: **App para computador** → **Criar**
4. **Baixar JSON**
5. Renomeie para `client_secret.json` e ponha na **raiz do projeto** (ao lado do `cortai.py`)

### 5. Autorizar

```powershell
python cortai.py youtube auth
python cortai.py youtube status    # confere
```

Abre o navegador, você escolhe a conta, aceita. O token fica em
`work/youtube_token.json`.

### 6. Publicar

```powershell
python cortai.py publish --clip 15 --privacy unlisted
```

Ou clique em **publicar no YouTube** no card do clipe. O envio roda em segundo plano,
o card mostra o progresso e depois o link.

Para publicar sozinho quando o clipe for aprovado:

```json
"publish": {
  "auto": true,
  "auto_min_score": 7.5,
  "privacy": "unlisted",
  "category_id": "20"
}
```

`auto_min_score` é o **termômetro**: a nota é de 0 a 10, então `7.5` só publica clipe
de nota 7,5 pra cima. Ajuste pelo painel em *configurações → publicação*. O painel
mostra o limiar ativo no topo (`auto ≥7.5`), para não passar despercebido.

### Fila, retry e horário de postagem

Publicar não é imediato: vai para uma fila e o supervisor processa a cada 30s.

```json
"publish": {
  "schedule_hours": [19, 20],
  "max_attempts": 5,
  "retry_minutes": 5
}
```

- `schedule_hours` vazio = publica assim que sair. Com `[19, 20]`, o upload é agendado
  para a próxima 19h ou 20h (usa `publishAt` do YouTube, que exige o vídeo `private`
  até a hora).
- `min_gap_minutes` (padrão `90`) **diversifica os horários**: depois de um upload, o
  próximo só sai quando o intervalo passa. Com vários clipes na fila, eles saem um a
  cada 90 minutos em vez de todos no mesmo minuto. Com `schedule_hours` definido, os
  horários são empilhados a partir do primeiro slot com esse espaçamento.
- Publicar manualmente (botão no painel ou `cortai.py publish <id>`) **ignora** o
  intervalo: você pediu aquele clipe agora.
- Se o upload falhar (rede, token expirado), ele volta para a fila com espera crescente:
  5, 10, 20, 40, 80 minutos, até `max_attempts`.
- Depois disso o clipe fica em `error` com o motivo e o botão **reenviar** no painel.

### Limite do YouTube (por que para de publicar)

O YouTube impõe **dois tetos** diferentes, e nenhum é configurável por nós:

| teto | erro | quando zera |
|---|---|---|
| cota de API do projeto (10.000 unidades/dia, 1.600 por upload ≈ 6 vídeos) | `quotaExceeded` | meia-noite do Pacífico |
| quantidade de uploads do canal por dia (varia por conta, é menor em canal novo) | `uploadLimitExceeded` | meia-noite do Pacífico |

Quando qualquer um dos dois aparece, o cortai **não trata como falha do clipe**: a fila
inteira pausa, o job continua `queued`, nenhuma tentativa é gasta, e tudo volta sozinho
depois do reset. No painel o clipe mostra `Limite do YouTube · volta 19/11 05:10`.

Para não bater na parede todo dia, dá para fixar seu próprio teto:

```json
"publish": { "max_per_day": 6 }
```

`0` (padrão) desliga o limite próprio. O contador é de clipes publicados com sucesso
desde a meia-noite local.

```powershell
python cortai.py queue            # o que está na fila
python cortai.py queue --drain    # processa os vencidos agora
```

### Clipes repetidos

Antes de gastar transcrição, o sistema consulta o banco: se o pico já está dentro de um
clipe existente (sobreposição ≥ 50% do intervalo), ele pula. Isso sobrevive a restart —
o dedupe em memória não.

### Três coisas que vão te morder

| problema | causa | saída |
|---|---|---|
| token morre em ~7 dias | app em modo **Teste** expira o refresh token | publique o app (verificação) ou reautorize |
| `quotaExceeded` | desde jun/2026 o upload tem balde próprio: **100 envios/dia por projeto** (antes era 1.600 unidades por upload, o que dava 6/dia — guias antigos ainda dizem isso) | espere o reset (meia-noite de Los Angeles) ou divida em mais projetos |
| `403` na primeira tentativa | API não ativada, ou seu e-mail fora dos usuários de teste | refaça os passos 2 e 3 |

> Relatos de canais novos batendo em `429` por volta de 7 envios/dia mesmo com a cota
> documentada sobrando (anti-spam de conta nova, não é a cota oficial). Se acontecer,
> o caminho é verificar o canal e postar em ritmo humano por alguns dias.

### Numa VPS / Docker

O token fica em `work/youtube_token.json`, e `work/` é volume do container — então
**autorizar na sua máquina já basta** para publicar dentro do Docker:

```bash
scp work/youtube_token.json usuario@vps:/caminho/cortai/work/
docker compose restart painel
```

O token carrega o `client_id`/`client_secret` dentro dele; o `client_secret.json` só é
necessário para autorizar de novo.

Se preferir autorizar de dentro do container, ponha o `client_secret.json` em `work/`
(é o diretório montado) e libere a porta do retorno do OAuth:

```bash
docker compose run --rm -p 8080:8080 painel python cortai.py youtube auth --port 8080
```

Não monte o `client_secret.json` na raiz: ele não é necessário lá e sobe junto no build.

## Docker

```bash
docker compose build
docker compose up -d
docker compose logs -f cortes
```

Sobe dois serviços com a mesma imagem: `cortes` (captura e cortes) e `painel`
(web em `8787`). O `work/` guarda buffer, banco e tokens; `out/` guarda os clipes.

```bash
docker compose run --rm painel python cortai.py passwd   # definir senha
docker compose run --rm painel python cortai.py youtube auth
```

Ou defina `PANEL_PASSWORD` no `.env` — o painel usa essa senha na primeira subida.
O container **se recusa** a abrir em `0.0.0.0` sem senha.

Imagem testada com Debian slim + ffmpeg do apt (tem libass) e opencv-headless.

## Integração com seu postador

Três opções, da mais simples à mais acoplada:

1. **Watcher de diretório** — varra `out/**/*.json`, poste, marque como enviado.
   Cada `.json` tem `title`, `hook`, `caption`, `hashtags`, `start_ts`, `end_ts`, `score`.
2. **SQLite** — tabela `clips`. Pegue `WHERE status='rendered'`, depois
   `UPDATE clips SET status='published', published=? WHERE id=?`.
3. **Hook Python** — em `cortai/worker.py`, após `db.add_clip`, chame seu módulo.

Nada aqui bloqueia: o clipe é gravado e o registro existe antes de qualquer postagem.

## Custo (medido, não estimado)

Cada chamada de ASR e de LLM registra o consumo real da API (segundos de áudio, tokens)
na tabela `usage`. O painel mostra o acumulado do dia.

Números observados numa live calma de GTA V:

| Etapa | Consumo | Custo |
|---|---|---|
| ASR `elevenlabs/scribe-v2` (via OpenRouter) | 22s de áudio | US$ 0,0014 |
| Juiz Jev | 2.400 tokens | US$ 0,0001 |
| Copy Gemini 2.5 Flash (só nos aprovados) | 1.600 in + 110 out | US$ 0,0008 |

~26 candidatos/hora numa live calma → **US$ 1,80/dia em 5 lives**. O custo está na
triagem, não no clipe.

Uma chave (OpenRouter) resolve LLM, juiz e transcrição. `GROQ_API_KEY` é opcional e
serve só como reserva mais barata.

Alavancas: ASR no Groq (US$ 0,0004/min, 9x mais barato que o scribe); `moments.peak_z`
mais alto gera menos candidatos; modelo de visão mais barato como primário. Preços em
`config.json` → `pricing` (edite quando as tabelas mudarem).

Fora a API: 5 lives 1080p60 ≈ 20 Mbps ≈ 72 GB/dia de download.

## Facecam

O sistema acha o quadradinho do streamer sozinho:

1. amostra ~20 frames da janela, detecta rostos com YuNet (OpenCV, CPU, <1s)
2. agrupa deteccoes por proximidade — o rosto que aparece no mesmo lugar 20 vezes é a facecam
3. expande rosto → camera (`pad`, padrão 2.6x) e encosta na borda mais próxima
4. rejeita se não estiver num canto (rosto no meio da tela não é facecam)
5. cacheia em `work/<slug>/facecam.json` e revalida a cada `facecam.refresh_s` (15 min)

Para conferir/forçar numa live específica:

```powershell
python cortai.py facecam canal1              # lê o buffer da live
python cortai.py facecam --file gravacao.mp4 # ou um arquivo
```

O LLM então escolhe o enquadramento **por clipe**:

| layout | quando | como fica |
|---|---|---|
| `pip` | jogada + reação importam (padrão) | gameplay cheio + facecam ampliada no canto |
| `face` | a reação É o conteúdo | zoom total na face, fundo desfocado dela mesma |
| `game` | rosto não reage ou não acrescenta | só gameplay |

No `pip` a facecam original do gameplay é desfocada, para não aparecer duplicada.

Ajustes: `facecam.pad` (3.4) se o recorte pegar muito do jogo ou cortar a cabeça;
`facecam.min_frame_hits` (0.3) se a detecção falhar em live com o streamer pouco visível;
`render.pip_scale` / `pip_position` (`tr`,`tl`,`br`,`bl`) / `pip_offset_y` para posicionar.

`facecam.provider` escolhe o motor:

| provider | como funciona | custo |
|---|---|---|
| `jev` (padrão) | pergunta à TypeSafe "tem facecam?" + "onde está?" — devolve a caixa real da webcam | US$ 0,0001, ~600ms |
| `yunet` | YuNet local + heurística de canto e tamanho de rosto | grátis, ~2s |

O `jev` não depende de canto nem de tamanho de rosto, e acha a caixa da câmera, não a
cara. O `yunet` fica como reserva quando não há chave do OpenRouter.

A detecção roda em resolução nativa (rosto de facecam em 1080p tem ~70px e morre em
downscale) e descarta rosto que se move muito, rosto grande demais (close de personagem
em cutscene) e rosto fora de canto. Se nada passar, fica sem facecam — layout `game`.

**Todo clipe aprovado que vai usar a cam é verificado antes de renderizar** — e só esses,
não os candidatos reprovados. O sistema extrai 3 frames do trecho e checa se há rosto no
retângulo. Streamers trocam a cam entre gameplay e cutscene; se o retângulo cacheado
falhar, ele redetecta dentro do próprio trecho e usa a posição nova (só nesse clipe).
Se nem isso achar, sai como `game` — nunca `pip` no chão.

## Duração do corte

O corte **não é fixo**. Para cada candidato, o modelo recebe uma janela de contexto
(`context_pre_s` 12s antes + `context_post_s` 25s depois do pico), vê a transcrição e
devolve `start_s`/`end_s` do trecho que vale a pena.

Depois disso o código ancora os limites:

1. **snap em fala** — o início volta para o começo da frase, o fim avança para o término.
   Não corta palavra nem reação no meio.
2. **piso** `min_clip_s` (10s) — se o modelo pedir menos, estende.
3. **teto** `max_clip_s` (37s) — se pedir mais, corta.

Se o modelo não devolver limites (gate heurístico, Jev puro), usa o fallback
`pre_roll_s`/`post_roll_s` em volta do pico.

## Legenda

Com timestamp por palavra (scribe-v2), a legenda sai no formato de clipe viral:
2–3 palavras por vez, grandes, e a palavra que está sendo falada acende em amarelo.
`karaoke_size` (96), `karaoke_words` (3) e `karaoke_accent` controlam isso.

Se o backend de ASR não devolver palavra (modelo sem timestamp, ou live sem fala),
cai automaticamente para a legenda por frase inteira.

`asr.keyterms` enviesa o reconhecimento para nomes e gírias do jogo ("GTA", "Trevor",
"Los Santos"). Melhora justamente onde o modelo mais erra. Se o provedor não aceitar,
o sistema refaz a chamada sem — não quebra.

## Limpeza automática

`out/` cresce para sempre: ~15 MB por clipe. A limpeza roda sozinha a cada
`maintenance.run_every_hours` (6h por padrão) e no start do supervisor.

```json
"maintenance": {
  "enabled": true,
  "clip_retention_days": 30,
  "keep_unpublished_days": 0,
  "db_retention_days": 90,
  "run_every_hours": 6
}
```

| campo | o que faz |
|---|---|
| `clip_retention_days` | apaga arquivos de clipe **publicado** com mais de N dias |
| `keep_unpublished_days` | clipe **não publicado**: `0` = nunca apaga |
| `db_retention_days` | apaga linhas de `log` e `usage` (custo) mais velhas que N dias |
| `run_every_hours` | intervalo entre limpezas |

A regra de segurança: **clipe que você não publicou nunca é apagado** por padrão.
Ele é o único artefato que não dá para regenerar. A linha do banco fica (com status
`purged`), então o histórico, a nota e o custo continuam contando.

Para ver o que sairia antes de apagar:

```powershell
python cortai.py purge --dry-run
python cortai.py purge
```

No painel: *configurações → limpeza de disco* tem **simular** e **limpar agora**.
Também apaga arquivos órfãos em `out/` que não pertencem a nenhum registro.

## Modelos e como trocar

| papel | padrão | onde trocar |
|---|---|---|
| Transcrição | `elevenlabs/scribe-v2` | `asr.models.openrouter` |
| Transcrição reserva | `whisper-large-v3-turbo` (Groq) | `asr.models.groq` |
| Transcrição reserva | `whisper-1` (OpenAI) | `asr.models.openai` |
| Gate/juiz | `typesafe/jev-1.14` | `classify.jev.model` |
| Copy (título, gancho, hashtags) | `z-ai/glm-5.3-flash` | `llm.providers[0]` |
| Copy reserva | `google/gemini-2.5-flash` | `llm.providers[1]` |
| Facecam | YuNet (ONNX local) | `models/yunet.onnx` |

Medido no mesmo clipe real (3 frames, ~1.700 tokens de entrada):

| modelo | tempo | custo/chamada | observação |
|---|---|---|---|
| `z-ai/glm-5.3-flash` | 2,7s | **US$ 0,00073** | escolhido |
| `google/gemini-2.5-flash` | 3,1s | US$ 0,00104 | reserva |
| `qwen/qwen3.7-flash` | — | — | **400: data inspection** — recusou conteúdo de GTA |
| `deepseek/deepseek-v4.1-flash` | — | — | resposta vazia, não suporta `json_object` |

Dois aprendizados que não estão no preço: alguns provedores **recusam conteúdo de GTA**
(violência, nudez) no meio do lote, e modelo pequeno sem suporte a `response_format`
devolve texto vazio. Teste antes de trocar.

O custo exibido no painel vem do campo `usage.cost` da resposta, não de tabela — imagem
tem preço próprio por provedor e a tabela mentiria.

`classify.copy_frames` (padrão 3) controla quantos frames vão para a copy. O Jev já
julgou com todos; a copy precisa de menos. Zerar deixa a chamada só texto (mais barata,
mas título pior em momento sem fala).

As transcrições testadas e o custo por minuto:

| modelo | US$/min | timestamp por palavra |
|---|---|---|
| `elevenlabs/scribe-v2` | 0,0037 | sim |
| `deepgram/nova-3` | 0,0043 | sim |
| `openai/whisper-large-v3` | 0,0015 | não |
| `whisper-1` (OpenAI direto) | 0,0060 | não |

Sem timestamp por palavra a legenda cai para o modo frase inteira — funciona, mas
perde o efeito de destaque.

**A cadeia de transcrição** (`asr.chain`) é tentada em ordem: se a chave não existe ou
o modelo falha, passa para o próximo. Para usar só um:

```json
"asr": { "chain": ["openrouter"] }
```

**A cascata de copy** (`llm.providers`) aceita qualquer endpoint OpenAI-compatible —
OpenRouter, OpenAI direto, Groq, Ollama local. A primeira da lista que responder ganha;
as seguintes entram quando ela cai (`cooldown_s` de 180s antes de voltar).

```json
"llm": {
  "providers": [
    { "name": "barato", "kind": "openai",
      "base_url": "https://openrouter.ai/api/v1",
      "model": "google/gemini-2.5-flash", "key_env": "OPENROUTER_API_KEY" }
  ]
}
```

`kind: "anthropic"` fala a API nativa da Anthropic (sem OpenRouter no meio).

Mudou modelo de ASR ou de copy? **Reinicie o supervisor** — os clientes são criados uma
vez. Limiares, vídeo, marca e publicação mudam no próximo ciclo, sem reiniciar.

## Ajuste fino para o lançamento do GTA VI
- `moments.peak_z` (1.3): baixe para `1.0` nos primeiros dias. Chat e áudio vão
  saturar; gate alto demais perde o pico, baixo demais gera lixo. Meça.
- `moments.min_sep_s` (45): suba para `90` se sair clipe repetido do mesmo evento.
- `classify.min_score` (7.0): é o filtro final. 7 dá ~1 clipe a cada 20–30 min de live
  movimentada. 8+ é seco, 6 é spam.
- `live.window_s` (60): janela de análise. Menor = reage mais rápido, corta menos
  contexto. Não desça de `pre_roll + post_roll + cycle`.
- `render.mode`: `pad_blur` (nada é cortado, barras desfocadas) ou `crop`
  (zoom 9:16 que **segue o movimento** — o recorte horizontal vem do centro de
  movimento dos frames, não mais de um `focus_x` fixo).

### Onde o CPU vai

Medido nesta máquina (Windows, sem GPU no caminho de vídeo):

| etapa | custo |
|---|---|
| concat do ring (cópia) | 0,11s |
| análise de áudio | 0,02s por minuto |
| enquadramento por movimento | 0,45s por clipe |
| confirmação de facecam | 0,35s por clipe |
| **render 1080x1920** | **3,8s (game) / 8,6s (pip) por 18s de clipe** |

O render domina. A cadeia descarta frames na entrada (`fps=30`), o que cortou ~40%
em live de 60fps — antes filtrava 60 e entregava 30.

Codificar em GPU (`h264_amf`) **não ajuda**: 7,5s contra 6,8s. O gargalo é o
filtergraph (escala, blur, overlay, libass), que roda em CPU de qualquer jeito.

Em 5 lives com 1 clipe/hora cada, isso dá menos de meia CPU. CPU não é o limite.

## Limites reais deste MVP
- **A facecam é um retângulo fixo**: achado uma vez, reaproveitado. A confirmação por
  clipe evita o pior (PIP no lugar errado), mas se o streamer muda a cam no meio de um
  mesmo trecho, aquele trecho sai sem facecam.
- **Reiniciar a captura limpa o buffer**: o ffmpeg recomeça a numeração dos segmentos,
  então segmentos antigos são descartados. Você perde o histórico, não ganha clipe corrompido.
- **A facecam é achada por rosto**, não por borda da caixa. Streamer sem rosto em cena
  (câmera desligada, de costas) não é detectado — cai em layout `game`, sem quebrar.
- **Reframe do jogo é fixo**: centro ou blur. Não segue a ação. Sem GPU, tracking em
  tempo real de 5 streams não cabe. A facecam é o único enquadramento dinâmico.
- **O LLM vê 3 frames**, não o vídeo. Ele acerta reação+contexto, mas pode perder
  algo que só aparece em movimento.
- **ASR erra nome de jogo e gíria.** O prompt manda ignorar, mas legenda pode sair torta.
- **Buffer só em disco**: se o disco encher, a captura para. `doctor` mostra espaço livre.
- **GTA VI**: cada live 1080p60 consome ~4 Mbps de download. 5 simultâneas = 20 Mbps
  e ~1,5 GB de buffer.

## Aviso de conteúdo

Clipe de live de terceiro é uso de obra alheia. Twitch ToS, política de conteúdo da
Rockstar e a regra de "conteúdo reutilizado" do YouTube se aplicam ao que **você
publica**, não ao que este software corta.

A regra que o projeto adota: **só clipear canal que autoriza**. Muitos streamers têm
programa de clipping (alguns pagam por view), outros proíbem no chat ou nos termos.
Quando o canal não autoriza, o corte continua tecnicamente possível e continua sendo
um problema seu — inclusive derrubando monetização por conteúdo reutilizado.

O software não verifica permissão, não pergunta e não avisa. Essa parte é sua.

## Estrutura

```
cortai.py                CLI
pipeline/                motor: áudio, detecção de picos, render, ASS
  audio.py               STFT -> loudness/flux/centroid por segundo
  moments.py             fusão de sinais, z-score robusto, picos
  render.py              9:16, legenda queimada, corte
live/                    camada tempo real
  capture.py             streamlink -> ffmpeg segmentado
  ring.py                buffer circular + GC
  worker.py              ciclo: janela -> gate -> ASR -> LLM -> corte
  supervisor.py          N workers, restart, shutdown
  asr.py                 groq -> openai -> local
  llm.py                 roteador OpenRouter (BYOK) com fallback
  classify.py            prompt + frames + escolha de layout
  facecam.py             deteccao do quadrado do streamer (YuNet)
  branding.py            logo, @handle, CTA
  chatlive.py            sinal de chat ao vivo
  dashboard.py           snapshot do estado para o painel
  server.py              painel web (stdlib) + preview + midia
  preview.py             remux curto do ring para o preview
  db.py                  SQLite
```

## Licença

MIT — veja [LICENSE](LICENSE). Uso comercial liberado: pode rodar no seu canal,
adaptar e redistribuir, mantendo o aviso de copyright.

O que a licença **não** cobre: o conteúdo que você clipeia. Direito sobre a live é do
streamer, e a permissão dele é um acordo entre vocês, fora deste repositório.
