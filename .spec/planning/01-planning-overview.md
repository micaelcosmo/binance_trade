# 01 · Planning Overview — Spec-Driven Development

> **Status:** Draft inicial · **Branch:** `micael_development_web-view` · **Versão atual:** ~v3.6.6
> **Escopo deste doc:** visão geral do estado atual (o que existe, o que é bom, o que é ruim) e o plano de melhoria que guiará as specs subsequentes.
> **Regra de ouro deste repositório:** `user.cfg` e `.env` **nunca** são lidos, versionados ou ecoados. Apenas os templates `*.exemple`.

---

## 0. Como este `.spec/` funciona (convenção)

Adotamos **spec-driven development**: nada de código novo significativo sem uma spec correspondente. A pasta organiza-se assim:

```text
.spec/
├── planning/        # visão, roadmap, decisões macro (este doc vive aqui)
├── specs/           # specs de features/refactors individuais (00x-nome.md)
├── adr/             # Architecture Decision Records (decisões irreversíveis)
└── contracts/       # contratos de dados (schemas JSON/flags/eventos socket)
```

Convenção de nomes: `NN-kebab-case.md` (prefixo numérico = ordem de leitura).
Cada spec passa por: `Draft → Review (Micael) → Approved → Implemented → Verified`.
Trechos de **baixo nível** (schemas, estados, contratos) vão como **YAML dentro do markdown** para serem máquina-legíveis e diffáveis.

---

## 1. Visão do produto (alto nível)

**Binance Trade Bot Pro — AI Edition** é um terminal de trading algorítmico para swing trade curto de cripto na Binance. A tese central é uma **decisão em duas camadas**:

1. **Camada matemática (Porteiro Python)** — barata, determinística, filtra ruído.
2. **Camada preditiva (Comitê de IA / Gemini)** — cara, probabilística, só decide sobre o que já passou no filtro.

O valor está exatamente nessa ordem: a IA nunca vê "facas caindo" sem contexto, o que economiza tokens e reduz alucinação. O operador (Micael) supervisiona por um painel em tempo real e pode intervir (panic button, ajuste de agressividade, swap).

---

## 2. Estado atual — arquitetura real

```text
UI (Flask app.py / Tkinter painel.py)
        │  escreve flags  ▲ lê bot_status.json
        ▼                 │
   [ arquivos no disco: *.flag, bot_status.json, *_state.json ]
        │                 ▲
        ▼  consome flags  │  escreve estado
MOTOR (binance_trade_bot/ → profit_gain_strategy.py)
        │
        ├── get_enriched_data()  → indicadores (pandas-ta)
        ├── scan_market()        → Porteiro Python + orquestração
        ├── ai_agent.analyze_*() → Gemini 2.5 Flash
        └── execute_real_trade() → ordens a mercado (python-binance)
```

Mapa low-level dos componentes e seu peso:

```yaml
components:
  - path: binance_trade_bot/strategies/profit_gain_strategy.py
    role: motor quantitativo principal (estado + decisão + execução)
    loc: 1038
    health: alto-risco   # arquivo-deus, faz tudo
  - path: painel.py
    role: dashboard desktop (legado Tkinter)
    loc: 766
    health: legado       # duplica lógica de UI do app.py
  - path: app.py
    role: webview Flask + SocketIO
    loc: 518
    health: ativo
  - path: binance_trade_bot/binance_api_manager.py
    role: wrapper da API Binance
    loc: 450
    health: legado-herdado
  - path: binance_trade_bot/database.py
    role: persistência SQLAlchemy
    loc: 295
    health: pouco-usado  # profit_gain usa JSON, não o DB
  - path: binance_trade_bot/models/ai_agent.py
    role: comitê de IA (Gemini)
    loc: 165
    health: ativo
  - path: binance_trade_bot/config.py
    role: parse anti-crash do user.cfg
    loc: 95
    health: bom
contracts:
  state_file: bot_status.json        # motor → UI (poll ~1s)
  persist_motor: profit_gain_state.json
  persist_ui: gui_state.json
  command_flags:
    - force_sell.flag
    - reset_trades.flag
    - add_trade.flag
    - cooldown.flag
    - bb_std.flag
    - update_pending.flag
```

---

## 3. O que está BOM (manter / proteger)

- **Filtro em duas camadas.** A separação "matemática primeiro, IA depois" é a melhor decisão de design do projeto. Reduz custo e risco. → virar invariante de arquitetura num ADR.
- **Config anti-crash.** `config.py` com fallbacks institucionais e override por env var: sobrevive a `user.cfg` incompleto. Bom para deploy cloud.
- **Resiliência operacional.** Tratamento de `ConnectionError`/timeout, persistência de estado em JSON e **recuperação de posição** ao reiniciar (assume posições já abertas na carteira).
- **Desacoplamento UI↔motor.** Motor roda como processo separado; UI só observa estado e emite flags. Falha na UI não derruba o trading.
- **Gestão de risco em camadas.** Trailing stop + stop dinâmico por ATR + stop de desastre + Tribunal de Swap. A intenção de risco é madura.
- **Transparência ("caixa branca").** Dossiê visual + relatório da IA expostos no painel: auditável.

---

## 4. O que está RUIM (dívida técnica / risco)

```yaml
issues:
  - id: ARCH-01
    title: "Arquivo-deus profit_gain_strategy.py (1038 LOC)"
    severity: alta
    detail: >
      Estado, indicadores, filtro, chamada de IA, execução de ordem, persistência e
      geração de payload da UI vivem na mesma classe. Difícil testar e evoluir.
  - id: ARCH-02
    title: "Lógica de UI duplicada (painel.py vs app.py)"
    severity: media
    detail: Duas interfaces mantêm cópias da mesma lógica de flags/estado. Drift garantido.
  - id: SEC-01
    title: "Flask inseguro para exposição"
    severity: CRITICA   # DECIDIDO: acesso remoto planejado → P0 crítico
    detail: >
      SECRET_KEY hardcoded, debug=True, host=0.0.0.0, sem auth nem HTTPS.
      Como haverá acesso remoto, isto expõe controle total do bot (incl. venda forçada)
      e RCE via debugger do Flask. Bloqueante antes de qualquer exposição.
  - id: SEC-02
    title: "Segredos em user.cfg"
    severity: alta
    detail: Confirmar .gitignore; garantir que chaves Binance/Google nunca vazem em commit/log.
  - id: TEST-01
    title: "Ausência de testes automatizados"
    severity: alta
    detail: Nenhuma cobertura. Refactor do motor é cego sem testes de regressão.
  - id: DATA-01
    title: "Contrato bot_status.json implícito"
    severity: media
    detail: Schema do estado vive espalhado no código; UI e motor podem divergir silenciosamente.
  - id: DATA-02
    title: "Concorrência de arquivos-flag / JSON"
    severity: media
    detail: Escrita/leitura sem lock; risco de race e leitura de JSON parcial.
  - id: DEPS-01
    title: "Conflito websockets==11.0.3"
    severity: baixa
    detail: unicorn-binance-websocket-api fixa versão antiga; pode quebrar em upgrades globais.
  - id: DEAD-01
    title: "Camada legada pouco usada"
    severity: baixa
    detail: database.py/models SQLAlchemy, auto_trader, estratégias default/multiple_coins — peso morto para o fluxo profit_gain.
  - id: AI-01
    title: "Saída da IA confiada sem schema rígido"
    severity: media
    detail: json.loads direto da resposta do Gemini; sem validação de schema → KeyError/decisão inválida possível.
```

---

## 5. Como podemos MELHORAR (estratégia de evolução)

Princípio condutor: **endurecer antes de expandir**. Primeiro segurança e testes, depois refactor, depois features.

### Fase A — Blindagem (sem mudar comportamento)
- Formalizar contratos como YAML em `.spec/contracts/` (estado + flags + eventos socket).
- **Resolver `SEC-01` (CRÍTICO — acesso remoto confirmado):** secret via env, `debug=False` em prod,
  **autenticação obrigatória** no painel, HTTPS/TLS (proxy reverso), e considerar bind restrito + allowlist.
  Sem isto, expor o painel = entregar controle total do bot (venda forçada) + RCE via debugger Flask.
- Resolver `SEC-02`: auditar `.gitignore`, garantir que chaves Binance/Google nunca vazem em commit/log.
- Validação de schema na saída da IA (`AI-01`) com fallback seguro para `NENHUMA`/`HOLD`.
- Escrita atômica de JSON/flags (write-temp + rename) para `DATA-02`.

### Fase B — Rede de segurança (testes)
- Testes de unidade para os filtros matemáticos (`get_enriched_data`, condições do Porteiro) com klines fixos (fixtures).
- Testes do gestor de risco (trailing/stop/desastre) com séries de preço simuladas.
- Mock do cliente Binance + do agente de IA → testar `scan_market` sem rede.

### Fase C — Refactor do motor (`ARCH-01`)
Quebrar o arquivo-deus em colaboradores coesos:

```yaml
proposed_modules:
  indicators.py:   "cálculo puro de indicadores → dataclass/dict, sem efeitos colaterais"
  gatekeeper.py:   "regras do Porteiro Python (filtro determinístico, testável)"
  risk_manager.py: "trailing, stop dinâmico, stop desastre, decisão de venda"
  position.py:     "estado da operação + persistência (load/save)"
  ui_state.py:     "montagem do bot_status.json a partir do estado"
  strategy.py:     "orquestra os acima (fica fino)"
```

### Fase D — Unificação de UI (`ARCH-02`)
- Eleger o `app.py` (web) como UI canônica; congelar `painel.py` ou rebaixá-lo a thin client.
- Extrair a "linguagem de comandos" (flags) para um módulo único compartilhado.

### Fase E — Limpeza (`DEAD-01`)
- Decidir por ADR: manter as estratégias legadas ou removê-las. Se a `profit_gain` é a única ativa, isolar/arquivar o resto.

---

## 6. Roadmap de specs (próximos arquivos)

```yaml
# Ordem confirmada pelo Micael: blindar → testar → refatorar.
backlog:
  - file: .spec/specs/001-secure-flask-and-secrets.md
    goal: resolver SEC-01 (CRÍTICO, acesso remoto) + SEC-02 sem alterar lógica de trading
    priority: P0
    note: subiu ao topo — exposição remota confirmada
  - file: .spec/contracts/state-and-flags.md
    goal: contrato YAML de bot_status.json, *_state.json e arquivos-flag
    priority: P0
  - file: .spec/specs/002-ai-output-validation.md
    goal: schema rígido + fallback seguro na saída do Gemini
    priority: P1
  - file: .spec/specs/003-atomic-state-io.md
    goal: escrita atômica de JSON/flags (anti-race)
    priority: P1
  - file: .spec/specs/004-test-harness.md
    goal: fixtures de klines + mocks Binance/IA + primeiros testes
    priority: P1
  - file: .spec/specs/005-engine-refactor.md
    goal: quebrar profit_gain_strategy.py nos módulos da Fase C
    priority: P2
    depends_on: [004-test-harness]
  - file: .spec/adr/0001-two-layer-decision.md
    goal: registrar o filtro matemática→IA como invariante
    priority: P2
  - file: .spec/adr/0002-legacy-fate.md
    goal: "PENDENTE — decisão sobre painel.py/SQLAlchemy/estratégias legadas (Micael adiará)"
    priority: P3
    status: deferred
```

---

## 7. Invariantes que NÃO podem quebrar (durante qualquer evolução)

- A IA **nunca** decide sobre ativo que não passou no Porteiro Python.
- O motor **nunca** depende da UI estar viva para operar/proteger uma posição.
- Compra exige confiança da IA **≥ 90%**; swap exige **≥ 95%**.
- Stops (dinâmico, desastre, trailing) têm prioridade sobre qualquer decisão de IA.
- `user.cfg`/`.env` **nunca** são lidos por ferramentas, logados ou commitados.

---

## 8. Decisões do Micael (registradas) + pendências

**Decidido em revisão:**
- ✅ **Exposição:** acesso remoto **planejado** → `SEC-01` reclassificado como **CRÍTICO/P0**. Spec de segurança vira o primeiro item do backlog.
- ✅ **Prioridade:** confirmada a ordem **"blindar → testar → refatorar"**.
- ✅ **Web-first:** o `painel.py` (Tkinter) **morre na v3** — toda evolução de UI mira exclusivamente o `app.py`/web. Deploy oficial via **Docker** (Dockerfile + compose.yaml na raiz). Resolve parcialmente o ADR-0002.
- ⏸️ **Restante do legado** (SQLAlchemy + estratégias `default`/`multiple_coins`): **decidir depois** → ADR pendente `0002-legacy-fate.md` (status `deferred`). Até a decisão, **não mexer**.

**Ainda em aberto (não-bloqueante para Fase A/B):**
1. Modelo de auth do painel remoto (usuário único/senha, token, OAuth, VPN-only?) — será detalhado na spec `001`.
2. Onde o painel remoto será hospedado (VPS própria, túnel tipo Cloudflare/ngrok, etc.) — afeta a estratégia de TLS.
