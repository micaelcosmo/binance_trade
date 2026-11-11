# UNIT-011 · Repaginação da página do app (E3)

- **Status:** Draft (em andamento)
- **Épico:** E3 · **Prioridade:** 2 · **Tasks:** T-030, T-031
- **ADRs:** ADR-0004, ADR-0008
- **Arquitetura:** `arch.yaml#components.web_template`, `#events`, `#data_contracts.files.bot_status.json`

## Objetivo
Redesenhar `templates/index.html` com visual amigável/futurista e sóbrio, mantendo todas as funções atuais do painel.

## Escopo
- Somente `templates/index.html` (HTML/CSS/JS do front). Back-end (`app.py`) e contratos inalterados.
- Preservar todos os eventos socket emitidos/escutados (`arch.yaml#events`) e todos os campos exibidos de `update_metrics` / `update_balance`, inclusive `chart_data`, dossiê, histórico, parecer IA, botões de ciclo (cooldown 15/30/45, BB std 2.0/1.8/1.5), venda forçada com confirmação, +1 tentativa, heartbeat colorido.
- Verificação visual com dados mock (T-031) — sem ligar o motor real.

## Fora de escopo
- Autenticação (UNIT-001) e mudanças de contrato.
- `painel.py` (deprecado).

## Critérios de aceite
- [ ] Nenhum evento ou campo do contrato deixou de ser tratado.
- [ ] Layout responsivo (desktop e celular), legível em tema escuro.
- [ ] Bibliotecas externas apenas via CDN com versão fixa (hoje socket.io 4.0.1 via cdnjs).
- [ ] Prints da verificação com dados mock anexados à task T-031.
- [ ] Aprovado pelo Micael.
