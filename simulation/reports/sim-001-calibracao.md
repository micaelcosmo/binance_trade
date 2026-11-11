# sim-001 — Calibração da profit_gain por simulação (épico E2)

- **Data:** 2026-11-11 · **Agente:** ag-sim · **Tasks:** T-020…T-023
- **Escopo:** `binance_trade_bot/strategies/profit_gain_strategy.py`: Porteiro, IA (substituída por oráculo mock), entrada, stoploss e stopwin.
- **Código:** `simulation/` (motor, mock, grade). Reproduzir com `python -m simulation.run_grid`. Os CSVs ficam em `simulation/reports/`.

---

## TL;DR

1. **A configuração atual perde dinheiro na simulação, e com folga.** São 789 trades na carteira (jul/2024 a out/2026) com **win rate de 74%** e **expectância de −0,30% por trade**. O retorno composto fica em **−93%** com o oráculo aprovando tudo. A causa é aritmética. O trade vencedor médio dá **+1,44%** e o stop médio dá **−5,37%**, então o break-even exigiria ~79% de acerto. A expectância **bruta** do Porteiro (antes de custos) é **+0,003%**, praticamente zero. O round-trip de taxa (0,2%) mais o slippage (0,1%) leva todo o resultado.
2. **Nenhuma das 101 variações ficou lucrativa com robustez.** A melhor combinação escolhida pelo IS foi `SMA200 diária do ativo` + `trail_drop 0,2` + `stop_mult 3`. Ela leva a carteira a **≈ break-even**: IS −16,7% contra −83,7% da baseline, OOS −2,0% contra −59,3%, expectância 0,00%/trade, drawdown máximo 48% contra 86%. Mas ela **não sobrevive** a premissas de execução piores. Com latência (checagem só no fechamento de 15m) a carteira IS cai para −80,8%. Com slippage de 0,2% cai para −75,3%.
3. **O ajuste mais robusto é um só: o gate de regime SMA200 diária.** Ele melhorou IS e OOS, nos dois modos (carteira e por moeda) e em todos os trimestres de baixa: em 2026Q2 ele simplesmente não opera. As demais mudanças de parâmetro são marginais (efeito da ordem de 0,05 a 0,1 p.p. por trade) e estão dentro do ruído.
4. **Recomendação:** aplicar o gate SMA200 (seguro, defensivo). Os ajustes finos de trailing e stop são opcionais. O ponto principal é uma decisão do Micael: **com o Porteiro atual a estratégia não tem edge que pague os custos**. Ou a IA real está filtrando muito melhor que qualquer score técnico testado (isso precisa ser medido, ver D-201), ou não vale operar all-in com dinheiro real antes de uma mudança estrutural.

---

## 1. Metodologia

### 1.1 Dados (T-020)
- São klines **públicos** (`/api/v3/klines`, sem autenticação) em 15m, 1h, 4h e 1d, guardados em `data/sim/*.csv.gz`, com 0 gaps.
- **11 moedas USDT** com perfis diferentes:
  - majors: BTC, ETH, BNB;
  - L1 voláteis: SOL, AVAX, ADA;
  - payments: XRP;
  - memes: DOGE e TRUMP (TRUMP vem do `supported_coin_list.exemple`);
  - oráculo: LINK;
  - L2: POL (também do `.exemple`).
- Período simulado: **15/07/2024 → 01/11/2026** (~27,5 meses; 15m desde 01/07/2024 para aquecimento; 1d desde 06/2023 para a SMA200). POL começa em 09/2024 e TRUMP em 01/2025.
- Regimes do BTC no período:
  - alta de Q3/24 a Q3/25 (63k → 114k);
  - baixa de Q4/25 a Q2/26 (114k → 58k);
  - recuperação em Q3/26 (84k).

### 1.2 Split
- **IS (calibração)** cobre os primeiros 70%, de 15/07/2024 a 22/02/2026: a alta e o início da baixa.
- **OOS (validação)** cobre os 30% finais, de 22/02/2026 a 01/11/2026: o fundo da baixa e a recuperação.
- A seleção usa **só o IS**. O score de seleção é um SQN pooled (expectância/desvio × √min(n,100)), com penalidade para n < 30 trades e para moedas negativas, e rebaixamento quando a carteira IS é negativa.
- O OOS só é reportado. Nenhuma variação foi criada depois de olhar o OOS.

### 1.3 Motor (T-021) — `simulation/engine.py`
- **Sem look-ahead.** A decisão acontece no fechamento de cada vela de 15m. Os timeframes 1h, 4h e 1d usam só velas cujo `open_time + intervalo <= T`. A ordem é executada no **open da vela seguinte**. Um teste adultera o futuro e verifica que as features e os sinais passados não mudam.
- **Porteiro fiel ao código:**
  - `min_24h_change <= −2×ATR%(1h)`, com o 24h rolante calculado nas velas de 15m;
  - `−15% <= change_24h <= +2,5%`;
  - toque na BB inferior: 15m nas últimas 3 velas ou 1h nas últimas 2;
  - volume 15m ≥ 80% da média das 10 anteriores;
  - preço < EMA21(1h) −1%.
- **Saída fiel ao código:**
  - trailing ativa em +1,5% e vende num recuo de 0,3 p.p. do pico;
  - stop = clamp(ATR%×4): **BTC 6–10,5%** (o código usa `max(6.0, …)`, não 4) e alts 4–7%;
  - disaster −15%.
- **Disciplina:** máximo de 3 trades por dia, meta diária de 5% (soma de %, como o live), dia em UTC−3 e cooldown de 45 min após veto. Entrada all-in de 99%.
- **Execução:** feita na `MockExchange`, com taxa de 0,1% por lado e **slippage de 0,05%** contra o usuário. O P/L é calculado sobre o fill real.
- **Stop conservador (modo `intrabar`, o padrão):**
  - se a mínima toca o stop, sai no stop, mesmo que a máxima da mesma vela tenha batido o alvo (pior caso);
  - em gap, sai na abertura;
  - sem stop na vela, o caminho é O→L→H→C (vela de alta) ou O→H→L→C (vela de baixa).
- **Modo `close`:** checa só no fechamento de 15m, para medir a latência.
- **Modos de conta:**
  - **carteira**: uma posição por vez entre as 11 moedas, escolhendo a candidata de maior score, igual ao live;
  - **por moeda**: uma conta por moeda, para medir a robustez entre perfis.
- **O que NÃO é simulado:**
  - **o Gemini.** No lugar dele há um *oráculo mock*: um score de confluência das técnicas do doc 001.
    - Pesos: RSI(2) 15m virando de <10 (2), divergência RSI 1h (2), divergência MACD 1h (1), IBS 1h<0,2 (1), estocástico 15m cruzando <20 (1), MACD 1h virando (1), rejeição de fundo 1h (1), candle 15m de alta (1), toque 15m+1h (1), ativo > SMA200 (1), BTC > SMA200 (1).
    - Penalidade: −3 quando ADX 4h > 30 com DI− dominante.
    - Com `score_min=None` o oráculo aprova tudo que passa no Porteiro, e essa é a baseline.
  - o Tribunal de Swap;
  - as flags da UI;
  - a vela aberta: o live calcula os indicadores incluindo a vela corrente, e aqui só entram velas fechadas.

### 1.4 Grade (T-022) — 101 variações × 11 moedas × 2 modos
- **Estágio 1 (69 variações):** uma variável de cada vez a partir da BASE.
  - Entrada: ATR×{1; 1,5; 2,5; 3}, BB std {1,5–2,5}, volume {0–150%}, EMA {−0,5; −2; −3}, SMA200 {ativo, BTC, ambos}, veto ADX4h {25, 30, 40}, RSI2 virando, score ≥2…7, sem limite diário.
  - Stopwin: ativação 0,8–3%, recuo 0,2–1%, pares ativação/recuo, TP fixo de 1–3%, alvo AVWAP.
  - Stoploss: mult 2–6, clamps, disaster 5%, tempo máximo de 12–72h.
- **Estágio 2 (20 variações):** combinações dos 3 melhores de cada grupo (entrada, ganho, perda), escolhidos pelo IS.
- **Checagens (12):** BASE e o top-5 no modo `close` (latência) e com slippage de 0,2%.

---

## 2. Resultados

### 2.1 Baseline × melhores (carteira, fiel ao live)

| Variação | n IS | Ret IS | DD IS | Exp/trade IS | n OOS | Ret OOS | DD OOS | Exp/trade OOS |
|---|---|---|---|---|---|---|---|---|
| **BASE (atual)** | 587 | −83,7% | 86,3% | −0,26% | 202 | −59,3% | 61,6% | −0,40% |
| BASE @close (latência) | 460 | −92,7% | 92,9% | −0,50% | 180 | −54,0% | 65,2% | −0,38% |
| BASE @slippage 0,2% | 587 | −97,2% | 97,2% | −0,56% | 202 | −77,7% | 77,8% | −0,70% |
| sma200=asset (só o gate) | 390 | −41,0% | 63,4% | −0,09% | 59 | −15,0% | 24,9% | −0,24% |
| **REC = sma200=asset + trail_drop 0,2 + stop_mult 3** | 410 | **−16,7%** | 48,2% | **−0,00%** | 69 | **−2,0%** | 21,1% | **0,00%** |
| REC @close (latência) | 353 | −80,8% | 85,2% | −0,39% | 59 | −39,1% | 42,6% | −0,80% |
| REC @slippage 0,2% | 410 | −75,3% | 77,7% | −0,30% | 69 | −20,2% | 27,4% | −0,30% |
| Top-1 do score IS (REC + ema<−2%) | 373 | −39,1% | 56,4% | −0,10% | 63 | −24,7% | 29,7% | −0,41% |
| score≥5 (oráculo) | 381 | −57,6% | 69,7% | −0,18% | 132 | −21,1% | 33,0% | −0,14% |

Win rate em praticamente todas: 70–78%. Profit factor: BASE 0,78 e REC 1,00.

### 2.2 Por moeda (pooled, expectância líquida por trade)

| Variação | n IS | Exp IS | n OOS | Exp OOS | Moedas positivas OOS |
|---|---|---|---|---|---|
| BASE | 4325 | −0,30% | 1459 | −0,20% | 2/11 |
| sma200=asset | 1730 | −0,20% | 350 | −0,13% | 5/11 |
| REC | 1828 | −0,14% | 380 | −0,11% | 4/11 |
| Top-1 score IS | 1373 | −0,11% | 268 | −0,08% | 3/11 |

REC na carteira, período inteiro, por moeda:
- **positivas:** XRP +32%, LINK +17%, ETH +16%, POL +15%, AVAX +7%;
- **negativas:** BTC −26%, BNB −22%, DOGE −19%, SOL −15%, ADA −5%, TRUMP −3%.

O BTC é ruim porque o clamp de 6% faz o stop ser grande demais para a volatilidade dele. Não há padrão estável por perfil de moeda, o que é sinal de ruído.

### 2.3 Por trimestre (carteira; retorno composto do trimestre)

| Trimestre | BASE | sma200=asset | REC |
|---|---|---|---|
| 2024Q3 | −23,3% | −15,3% | −9,0% |
| 2024Q4 (alta forte) | +23,3% | +50,2% | +39,2% |
| 2025Q1 | −41,6% | −25,2% | −22,0% |
| 2025Q2 | +10,9% | −2,6% | −3,2% |
| 2025Q3 | −18,7% | −11,6% | +6,3% |
| 2025Q4 (início da baixa) | −46,8% | −29,3% | −19,7% |
| 2026Q1 | −42,6% | +1,7% (6 trades) | +2,0% (6 trades) |
| 2026Q2 (fundo) | −35,1% | sem trades | sem trades |
| 2026Q3 (recuperação) | −17,5% | +2,9% | +14,4% |
| 2026Q4 (out) | −18,8% | −17,4% | −14,3% |

O gate SMA200 corta quase todo o prejuízo da baixa (2025Q4–2026Q2). Ainda assim, mesmo em alta, a estratégia alterna trimestres positivos e negativos.

### 2.4 O que cada alavanca fez (estágio 1, por moeda, expectância IS → OOS; BASE −0,30 → −0,20)

- **Ajudou de forma consistente:**
  - SMA200 do ativo: −0,20 → −0,13;
  - SMA200 ambos: −0,21 → −0,14.
- **Ajudou pouco (dentro do ruído):**
  - trail_drop 0,2: −0,26 → −0,17;
  - stop_mult 3: −0,25 → −0,21;
  - EMA < −2%: −0,26 → −0,14;
  - EMA < −3%: −0,25 no IS, mas +0,14 no OOS (melhor OOS da grade, porém ruim no IS: não selecionável sem *data snooping*);
  - ATR×1,5: −0,27 → −0,20.
- **Neutro:** BB std 1,5–2,5, volume 0–150%, clamps, disaster 5%, limite diário.
- **Piorou:**
  - TP fixo, de −0,44 a −0,66;
  - alvo AVWAP: −0,50 / −0,60;
  - trailing com recuo ≥ 0,5;
  - timeout de 12–24h;
  - veto ADX 4h >25;
  - RSI(2) como gate obrigatório: −0,33.
  - Ativação de 2,5–3%: pior no IS (−0,40/−0,47), quase zero no OOS.
- **Oráculo mock (score):** não melhorou o IS em nenhum limiar (score≥3: −0,31; ≥5: −0,36; ≥7: −0,49). Confluência técnica **não** substituiu um filtro de qualidade. No OOS os limiares altos melhoram (≥7: +0,03), mas com poucos trades e sem confirmação no IS.

### 2.5 Latência e execução
- A checagem só no fechamento de 15m (`@close`) piora a expectância em 0,2–0,4 p.p. por trade. O stop é executado bem abaixo do nível. O live faz scout a ~60 s, mais a varredura completa antes do stop (parecer 000 §2), então fica **entre** o modo `intrabar` e o `close`.
- Como a expectância bruta da REC (+0,30%) é ≈ o custo do round-trip (0,30%), **qualquer** piora de execução a deixa negativa.

---

## 3. Riscos de overfitting e limitações

- Foram testadas 101 variações sobre o mesmo histórico. Ganhos de ~0,1 p.p. por trade estão dentro do que se espera por sorte. Por isso só o gate SMA200, que tem efeito grande e consistente em IS, OOS, modos e trimestres, entra como "seguro".
- O OOS da carteira tem só 59–69 trades na REC, porque o gate desliga a estratégia na baixa. É pouca amostra.
- **O Gemini real não foi simulado.** Se a IA aprovar só uma fração muito melhor que a média das candidatas, o resultado real pode ser outro. O mock testado (score técnico) não conseguiu isso. Nada aqui prova que a IA consegue ou não.
- Indicadores só com velas fechadas: o live usa a vela aberta (volume parcial, BB e EMA em movimento). O live dispara em momentos ligeiramente diferentes.
- Tribunal de Swap não simulado: ele raramente dispara (parecer 000 §5).
- O modelo de caminho intra-vela (O→L→H→C / O→H→L→C) é uma heurística. O stop sempre tem prioridade (pior caso).
- O retorno "por moeda" pooled concatena contas diferentes. Use as expectâncias e as moedas positivas, não o `ret_total_pct` dessa linha.

---

## 4. Recomendação

### 4.1 Tabela de parâmetros

| Parâmetro | Atual | Recomendado | Justificativa | Classe |
|---|---|---|---|---|
| Gate de regime (novo) | — | **comprar só se fechamento diário do ativo > SMA200 diária** (última vela 1d fechada) | Única alavanca com efeito grande e consistente: carteira IS de −84% para −41%, OOS de −59% para −15%, desliga a estratégia no bear de 2025Q4–2026Q2. Coerente com o doc 001 §1 | **Seguro aplicar** (só reduz trades) |
| `trailing_drop_pct` | 0,3 | **0,2** | Marginal (+0,04 p.p./trade IS). Exige execução rápida: piora mais que o 0,3 com latência | Opcional (com o gate) |
| Multiplicador do stop ATR | 4,0 | **3,0** (alts continuam com clamp 4–7) | Marginal. Para alts o piso de 4% domina e quase nada muda. Perdas médias de −5,4% para −4,9% | Opcional (com o gate) |
| `trailing_activation_pct` | 1,5 | **manter 1,5** | 0,8–1,2 sobe o win rate para 81–85% mas piora a expectância. 2–3% é pior no IS | Manter |
| TP fixo / alvo AVWAP | — | **não adotar** | Piores que o trailing em IS e OOS | Não aplicar |
| Tempo máximo de posição | ∞ | **não adotar** | 12–72h pioram ou ficam neutros | Não aplicar |
| ATR×, BB std, volume %, EMA −1% | 2,0 / 2,0 / 80 / −1 | **manter** | Variações dentro do ruído. EMA −3% foi o melhor OOS mas ruim no IS (não selecionável) | Manter |
| Veto ADX 4h, RSI(2) virando | — | **não adotar como gate** | Pioraram o IS | Não aplicar |
| Clamp de stop do BTC | 6–10,5 | **decisão do Micael** (ver D-203) | O BTC é a pior moeda na REC (−26%). 3–6% foi neutro no pooled | Decisão |
| `max_daily_trades` / meta 5% | 3 / 5% | **manter** | Sem limite fica igual no IS e pior no OOS | Manter |

### 4.2 Decisões abertas para o Micael (registradas no devpanel)

- **D-201 — A estratégia não paga os custos.** Mesmo a melhor variação fica em break-even e é frágil. Opções:
  - (A) colocar a IA em shadow-mode: logar todos os dossiês e vereditos e medir no futuro o acerto das aprovações contra as candidatas vetadas, antes de operar all-in;
  - (B) seguir operando com o gate SMA200 e tamanho reduzido;
  - (C) pausar o live até uma revisão estrutural (alvo/risco).
  - **Recomendação: A + B com tamanho reduzido.**
- **D-202 — Custos.** O edge bruto ≈ custo. Opções:
  - (A) ativar o desconto de taxa em BNB (0,075%/lado, −0,05 p.p. por round-trip);
  - (B) manter.
  - **Recomendação: A.**
- **D-203 — Stop do BTC.** O clamp 6–10,5% está largo para a volatilidade do BTC. Opções:
  - (A) manter;
  - (B) unificar com as alts (4–7%);
  - (C) 3–6%.
  - **Recomendação: manter (A) até uma rodada específica.** O efeito pooled foi neutro.
- **D-204 — Relação risco/retorno estrutural.** Com o alvo efetivo em ~+1,2–1,5% e o stop em 4–7%, a estratégia precisa de >79% de acerto. Revisar a tese ("repique de +2% em 14h" no prompt) e o all-in é escopo de uma nova spec, não de calibração.

---

## 5. Arquivos

| Arquivo | Conteúdo |
|---|---|
| `simulation/reports/sim-001-grid.csv` | métricas por variação × modo × segmento (IS/OOS/ALL), com `score_is` |
| `simulation/reports/sim-001-por-moeda.csv` | métricas por variação × moeda × segmento |
| `simulation/reports/sim-001-params.json` | parâmetros completos de cada variação |
| `simulation/reports/sim-001-trades-BASE.csv` | trades da baseline (carteira) |
| `simulation/reports/sim-001-trades-REC.csv` | trades da recomendada (carteira) |
| `simulation/reports/sim-001-trades-C_sma200_asset_ema_dist_-2.0_trail_drop_0.2_stop_mult_3.0.csv` | trades do top-1 do score IS |

Métricas: `n`, `win_rate`, `ret_total_pct` (composto, all-in 99%), `expectancy_pct` (média líquida por trade), `profit_factor`, `max_dd_pct` (inclui a pior excursão dentro do trade), `avg_hold_h`, `pct_stop`/`pct_trail`/`pct_tp`/`pct_timeout`, `trades_per_month`.
