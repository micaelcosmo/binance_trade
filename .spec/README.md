# `.spec/` — especificação, arquitetura e acompanhamento

Projeto: **Binance Trade Bot Pro — AI Edition**. Fluxo **spec-driven** (ADR-0001): nada de código novo significativo sem uma UNIT; toda mudança de arquitetura atualiza o `arch.yaml` no mesmo commit.

> **Regra inviolável (ADR-0003):** `user.cfg`, `.env` e qualquer `*.cfg`/`.env` real nunca são lidos, ecoados, logados ou commitados. Só os templates `*.exemple`.

## Estrutura

```text
.spec/
├── README.md        # este arquivo: convenções, ciclo de vida, índices
├── arch.yaml        # ÚNICO arquivo de arquitetura do projeto inteiro
├── STATUS.md        # gerado por devpanel/track.py — NÃO editar à mão
├── TEMPO.md         # gerado por devpanel/track.py — NÃO editar à mão
├── adr/ADR-NNNN-kebab.md
└── units/UNIT-NNN-kebab.md
```

| Artefato | Para quê | Quando muda |
|---|---|---|
| `arch.yaml` | componentes, runtime, contratos de dados (JSON/flags), eventos socket, serviços externos, parâmetros da estratégia, deploy, qualidade, dev tooling, roadmap, issues, invariantes | sempre que o código mudar algo descrito nele |
| `adr/` | decisão + contexto + consequências + status | decisão nova ou revisão de decisão (nunca apagar: marcar `Superseded by ADR-XXXX`) |
| `units/` | unidade de trabalho/spec: objetivo, escopo, fora de escopo, critérios de aceite, status, links | por ciclo de vida |
| `STATUS.md` / `TEMPO.md` | agentes, épicos, tasks, steps, decisões, eventos, tempos | só via `devpanel/track.py` |

## Convenções

- Idioma pt-BR, estilo técnico enxuto. Trechos de baixo nível em YAML.
- Nomes: `ADR-NNNN-kebab.md` (4 dígitos), `UNIT-NNN-kebab.md` (3 dígitos), numeração sequencial em ordem lógica; números nunca são reaproveitados.
- Referências cruzadas: `ADR-0007`, `UNIT-002`, `arch.yaml#secao.subsecao`.
- Cabeçalho de UNIT: Status, Épico/fase, Prioridade, Tasks, ADRs, Arquitetura (seções do `arch.yaml`), Origem.
- **Status de ADR:** `Proposed → Accepted | Deferred | Rejected → Superseded`.
- **Status de UNIT:** `Draft → Approved (Micael) → Implemented → Verified`.
  - *Approved*: o Micael revisou o escopo/critérios.
  - *Implemented*: código entregue.
  - *Verified*: critérios de aceite checados (testes/evidência).
  - UNIT de pesquisa: *Implemented* = análise entregue; *Verified* = revisada e acatada.
- Commits: semânticos com versão, só minor/patch (ADR-0011). Só o orquestrador commita (ADR-0010).

## Acompanhamento (STATUS/TEMPO e painel)

```bash
T=".venv/Scripts/python devpanel/track.py"     # sempre a partir da raiz do repo
$T agent ag-x --name "Nome" --kind worker --role "..." --status active --task T-020 --step "passo"   # heartbeat
$T task T-020 --status doing --agent ag-x --who ag-x
$T task T-020 --add-step "rodar grade" --estimate 90
$T task T-020 --step-doing "rodar grade"   |   --step-done "rodar grade"   |   --status done
$T event "mensagem" --who ag-x
$T decision D-101 --question "..." --options "A|B" --recommendation "A" --who ag-x [--blocking]
$T show
```

- Painel: `.venv/Scripts/python devpanel/server.py` → http://127.0.0.1:5055 (só leitura, atualiza a cada 3 s; cartão "Próxima interação" via `track.py proxima`, Links via `track.py link`, feed "Agora" via hook `devpanel/registrar_atividade.py`, card Testes via `devpanel/rodar_testes.py`). Decisões são respondidas no chat.
- Heartbeat: atualizar o agente a cada mudança de step (no máximo ~10 min).
- Decisões do dono: `--blocking` só se impedir de continuar; caso contrário seguir com a recomendação.

## Índice de ADRs

| ADR | Título | Status |
|---|---|---|
| [ADR-0001](adr/ADR-0001-spec-driven-e-estrutura-spec.md) | Spec-driven development e estrutura do `.spec/` | Accepted |
| [ADR-0002](adr/ADR-0002-decisao-em-duas-camadas.md) | Decisão em duas camadas: matemática antes da IA | Accepted |
| [ADR-0003](adr/ADR-0003-credenciais-nunca-lidas.md) | Credenciais nunca lidas, logadas ou versionadas | Accepted |
| [ADR-0004](adr/ADR-0004-web-first-painel-deprecado.md) | Web-first: `app.py` canônico, `painel.py` deprecado, Docker | Accepted |
| [ADR-0005](adr/ADR-0005-blindar-testar-refatorar.md) | Ordem: blindar → testar → refatorar | Accepted |
| [ADR-0006](adr/ADR-0006-auth-jwt-aaa.md) | Auth do painel: JWT/AAA via `user.cfg` | Accepted (impl. pendente) |
| [ADR-0007](adr/ADR-0007-ia-fail-closed.md) | Saída da IA: validação rígida, fail-closed | Accepted |
| [ADR-0008](adr/ADR-0008-ipc-por-arquivos-atomicos.md) | UI ⇄ motor por arquivos com escrita atômica | Accepted |
| [ADR-0009](adr/ADR-0009-destino-do-legado.md) | Destino do legado (SQLAlchemy, default, multiple_coins…) | Deferred |
| [ADR-0010](adr/ADR-0010-multi-agente-orquestrador-unico.md) | Multi-agente com orquestrador único + STATUS/TEMPO via `track.py` | Accepted |
| [ADR-0011](adr/ADR-0011-commits-semanticos-minor-patch.md) | Commits semânticos com versão; só minor/patch | Accepted |
| [ADR-0012](adr/ADR-0012-trabalho-no-disco-d.md) | Trabalho no disco D: | Accepted |
| [ADR-0013](adr/ADR-0013-testes-de-trading-so-com-mock.md) | Testes de trading só com mock | Accepted |

## Índice de UNITs

| UNIT | Título | Épico/fase | Status |
|---|---|---|---|
| [UNIT-001](units/UNIT-001-secure-flask-and-secrets.md) | Blindagem do painel web e gestão de segredos | Fase A · P0 | Draft (parcial) |
| [UNIT-002](units/UNIT-002-ai-output-validation.md) | Validação rígida da saída da IA | Fase A · P1 | Verified |
| [UNIT-003](units/UNIT-003-atomic-state-io.md) | Escrita atômica de estado | Fase A · P1 | Verified |
| [UNIT-004](units/UNIT-004-test-harness.md) | Test harness (pytest) | Fase B · P1 | Implemented |
| [UNIT-005](units/UNIT-005-engine-refactor.md) | Refactor do motor (arquivo-deus) | Fase C · P2 | Draft |
| [UNIT-006](units/UNIT-006-parecer-revisao-estrategias.md) | Pesquisa: parecer das estratégias | Pesquisa | Implemented |
| [UNIT-007](units/UNIT-007-15-tecnicas-validadas-profit-gain.md) | Pesquisa: 15 técnicas validadas | Pesquisa | Draft |
| [UNIT-008](units/UNIT-008-devpanel-acompanhamento.md) | Painel de acompanhamento de dev | E0 | Draft |
| [UNIT-009](units/UNIT-009-reestruturacao-spec.md) | Reestruturação do `.spec/` | E1 | Implemented |
| [UNIT-010](units/UNIT-010-simulacao-calibracao.md) | Simulação ≥ 50 variações (mock) | E2 | Draft |
| [UNIT-011](units/UNIT-011-repaginacao-pagina-app.md) | Repaginação da página do app | E3 | Draft |
| [UNIT-012](units/UNIT-012-calibracao-profit-gain.md) | Aplicar calibração na profit_gain | E4 | Draft |

## Mapa de migração (estrutura antiga → nova, 2026-11-11)

| Antigo | Novo |
|---|---|
| `planning/01-planning-overview.md` §0 convenção | ADR-0001 + este README |
| §1 visão, §2 arquitetura, §3 pontos fortes, §4 issues | `arch.yaml#system_context`, `#components`, `#strengths`, `#known_issues` |
| §5 fases A–E, §6 backlog | ADR-0005, `arch.yaml#roadmap`, UNIT-005 (Fase C) |
| §7 invariantes | `arch.yaml#invariants`, ADR-0002, ADR-0003 |
| §8 decisões do Micael | ADR-0004 (web-first/Docker), ADR-0005 (ordem), ADR-0006 (auth), ADR-0009 (legado deferred); pendências em UNIT-001 §9 |
| `specs/001..004-*.md` | UNIT-001..004 (texto integral) |
| `contracts/state-and-flags.md` | `arch.yaml#data_contracts`, `#events`; decisão em ADR-0008 |
| `strategies/000-parecer-revisao-estrategias.md` | UNIT-006 (texto integral) |
| `strategies/001-15-tecnicas-validadas-profit-gain.md` | UNIT-007 (texto integral) |
