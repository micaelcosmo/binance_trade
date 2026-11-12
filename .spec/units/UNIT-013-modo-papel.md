# UNIT-013 · Modo papel (paper trading) e view ao vivo no painel (E5)

- **Status:** Approved (pedido do Micael em 2026-11-11: "Modo papel… view que mostra esses testes acontecendo… obrigatoriamente no painel com fluxo")
- **Épico:** E5 · **Prioridade:** 0 · **Tasks:** T-060…T-066
- **ADRs:** ADR-0013 (testes de trading só com mock), ADR-0003 (credenciais nunca lidas)
- **Arquitetura:** `arch.yaml#dev_tooling.devpanel`, `#strategies.profit_gain`

## Objetivo
Rodar o **motor real** (`python -m binance_trade_bot`, estratégia profit_gain) de ponta a ponta sem tocar na conta:
preços reais de endpoints **públicos** da Binance, ordens e saldo numa exchange **simulada**, e um **stub determinístico**
no lugar do Gemini. O painel de dev ganha uma view ao vivo (gráficos + fluxo de decisões) e um card de resumo.

## Escopo
- Ativação: variável de ambiente `PAPER=1` (ou `paper_mode=true` em `[profit_gain]`). Em papel o motor **não** usa as chaves do
  `user.cfg` para nada (cliente sem chaves), não abre user-data stream e não chama o Gemini (`PAPER_AI=stub`, padrão).
- Saldo virtual inicial: `PAPER_SALDO_USDT` (padrão 1000). Taxa 0,1% e slippage 0,05% por lado (mesmo mock da simulação).
- Diário em `data/paper/` (gitignored), contrato abaixo. Escrita atômica para `estado.json`; append para `.jsonl`.
- Fora do escopo: mudar regras da estratégia; usar a IA real (fica para o shadow-mode da D-210/D-211).

## Contrato do diário (`data/paper/`)
```yaml
estado.json:            # reescrito a cada ciclo (atômico)
  modo: papel
  ia: stub                              # stub | gemini
  iniciadoEm: ISO-8601 local            # início do processo papel
  atualizadoEm: ISO-8601 local          # último ciclo (heartbeat)
  heartbeatEpoch: float
  pid: int
  saldoInicialUSDT: float
  usdt: float                           # saldo livre virtual
  equity: float                         # usdt + valor da posição a preço atual
  pnlPct: float                         # (equity / saldoInicial - 1) * 100
  trades: int
  ganhos: int
  perdas: int
  ciclos: int                           # scouts executados
  posicao:                              # null quando sem posição
    moeda: str                          # ex.: SOL
    simbolo: str                        # ex.: SOLUSDT
    qtd: float
    precoCompra: float                  # fill médio simulado
    precoAtual: float
    alvo: float                         # ativação do trailing
    stop: float                         # preço do stop ATR
    disaster: float                     # preço do disaster stop
    pico: float                         # maior P/L % visto
    plPct: float
    desdeEpoch: float
  ultimoScan:                           # resumo do último ciclo
    epoch: float
    moedas: int                         # varridas
    candidatas: int                     # passaram no Porteiro (antes do regime)
    bloqueadasRegime: int               # barradas pelo gate SMA200
    enviadasIA: int
    aprovadasIA: int
    resultado: str                      # texto curto (ex.: "MERCADO VETADO", "COMPRA APROVADA: SOL")
  funil:                                # acumulado desde o início
    varridas: int
    candidatas: int
    bloqueadasRegime: int
    enviadasIA: int
    aprovadasIA: int
    compras: int
    vendas: int
eventos.jsonl:          # 1 linha por evento
  {hora: ISO, epoch: float, tipo: scan|candidata|regime|ia|compra|venda|erro|inicio|fim,
   moeda: str|null, preco: float|null, detalhe: str (curto, ≤200),
   motivo: str|null (venda: trailing|stop_atr|disaster|forcada|swap), plPct: float|null}
equity.jsonl:           # 1 linha por ciclo
  {epoch: float, equity: float, usdt: float, posicao: float}
precos.jsonl:           # 1 linha por ciclo com posição aberta (moeda monitorada)
  {epoch: float, moeda: str, preco: float, alvo: float, stop: float}
```

## Critérios de aceite
- [ ] `PAPER=1 python -m binance_trade_bot` sobe, varre o mercado com dados públicos e grava o diário, sem ler credenciais nem chamar o Gemini.
- [ ] Ordens só na exchange simulada; nenhuma chamada autenticada à Binance (teste com cliente que falha em qualquer endpoint privado).
- [ ] Testes pytest do modo papel passam junto com a suíte (venv313).
- [ ] Painel: card "Modo papel" com botão para a view `/papel`; view com patrimônio, preço da posição com compra/venda/alvo/stop, fluxo de decisões com contagens e lista de eventos/trades, atualizando sozinha.
- [ ] Épico E5 aparece no fluxo do plano com as tasks.
