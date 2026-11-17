# branding/

Coloque aqui o `logo.png` do canal — PNG com fundo transparente, ~400px de largura.

Ele é sobreposto no canto configurado em `config.json` → `branding.logo_position`
(`tr`, `tl`, `br`, `bl`), com largura `logo_width`.

Sem esse arquivo nada quebra: o clipe sai só com `@handle` e CTA.

Outros campos em `config.json`:

| campo | o que faz |
|---|---|
| `handle` | `@seucanal`, desenhado acima do CTA |
| `cta` | texto do rodapé (`SEGUE PRA MAIS`) |
| `accent` | cor do CTA em `0xRRGGBB` |
| `font` | caminho de `.ttf`; vazio usa Arial Black do sistema |
| `handle_offset` / `cta_offset` | distância do rodapé em px (1080x1920) |
