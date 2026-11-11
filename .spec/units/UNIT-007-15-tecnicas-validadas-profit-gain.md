# UNIT-007 · Pesquisa · 15 técnicas de análise gráfica validadas para a profit_gain

- **Status:** Draft
- **Épico/fase:** Pesquisa/planejamento (insumo de E2/E4) · **Prioridade:** —
- **ADRs:** ADR-0002, ADR-0013
- **Arquitetura:** `arch.yaml#strategies.profit_gain`
- **Origem:** `.spec/strategies/001-15-tecnicas-validadas-profit-gain.md` (migrado integralmente em 2026-11-11, épico E1)

> **Situação atual:** Planejamento (2026-07-19) — nenhuma implementação. Texto integral abaixo. Candidatas a variações da simulação (UNIT-010) antes de qualquer adoção (UNIT-012).

<details><summary>Metadados originais</summary>

Título original: `001 — Planejamento: 15 Técnicas de Análise Gráfica Validadas para a profit_gain`

- **Data:** 2026-07-19
- **Natureza:** PLANEJAMENTO — nenhuma implementação neste documento.
- **Objetivo:** aprimorar a `profit_gain_strategy.py` com técnicas de leitura de gráfico (quando comprar / quando vender) já revisadas contra fontes externas, mitigando estratégias fake ou mal formadas.

</details>

---

## Metodologia de validação

Cada técnica só entrou na lista se passou por **pelo menos dois critérios**:

1. **Backtest publicado com números** (win rate, retorno por trade, taxa de reversão) em fonte que documenta a metodologia (QuantifiedStrategies, Alvarez Quant, Liberated Stock Trader com 120 mil trades testados, etc.);
2. **Estudo acadêmico ou uso institucional documentado** (papers em ScienceDirect/SSRN/arXiv, material educacional de corretoras reguladas — Fidelity, Schwab, Kraken);
3. **Coerência com a tese da profit_gain** (reversão à média em cripto, spot, janela de horas).

Técnicas populares que **falharam** na validação estão na seção "Descartadas" no fim — é a parte anti-fake deste documento.

Contexto do que a profit_gain **já usa** (para posicionar cada técnica como refinamento ou acréscimo): RSI 14 (4h/1h/15m), EMA 9/21 (1h), MACD 12/26/9 (1h/15m), ATR 14 (1h), Bollinger 20/2σ (1h/15m), volume 15m vs média de 10 velas, variação 24h, e o funil Porteiro matemático → IA (Gemini) → execução com trailing/stop ATR/disaster stop.

---

## As 15 técnicas

Organizadas por camada da estratégia onde atuam.

### Camada A — Regime de mercado (o que falta antes do Porteiro)

#### 1. Filtro de tendência macro (SMA 200 no diário)

- **O quê:** só operar reversão à média quando o preço (do ativo e/ou do BTC) está acima — ou não muito abaixo — da média móvel de 200 períodos no diário. É o filtro com maior evidência isolada que a pesquisa encontrou: numa análise de 100 mil+ backtests, a SMA200 como filtro binário de regime foi apontada como o indicador mais poderoso do dataset, por manter a estratégia fora dos grandes bear markets.
- **Onde encaixa:** novo gate no início do `scan_market()`, antes do loop de mineração. Hoje o único senso de "macro" da estratégia é o range de variação 24h (−15%…+2,5%) — ela não sabe se a queda de hoje acontece dentro de um mercado de alta (reversão provável) ou dentro de um bear market estrutural (faca caindo em câmera lenta).
- **Como (plano):** buscar klines diários (1 chamada extra por ciclo, cacheável por 24h) do BTC e do ativo candidato; calcular SMA200; expor `above_sma200_daily` e `btc_above_sma200` como booleanos no payload da IA e, opcionalmente, como veto duro configurável.
- **Por quê:** a maior fraqueza documentada de estratégias de reversão é operar contra regime. É o complemento macro que falta ao disaster stop — em vez de cortar o prejuízo depois, evita entrar no cenário que o gera.

#### 2. ADX como chave liga/desliga da reversão à média

- **O quê:** ADX abaixo de ~20–25 = mercado sem tendência (ambiente onde reversão à média funciona); ADX alto com DI− dominante = tendência de baixa forte (ambiente onde a "agulhada" é faca caindo). Material educacional da Fidelity/Schwab e guias quantitativos convergem: range strategies só com ADX < 20–25; backtests reportam redução de 30–40% em sinais falsos ao aplicar o filtro.
- **Onde encaixa:** `get_enriched_data()` — o `pandas_ta` já calcula ADX (`df.ta.adx()`); é um acréscimo natural ao conjunto de indicadores 1h.
- **Como (plano):** calcular ADX 14 no 1h e no 4h; adicionar `adx_1h`, `adx_4h` e `di_minus_dominant` ao payload; regra planejada: candidata com ADX 4h > 30 e DI− dominante não vai para a IA (veto do Porteiro).
- **Por quê:** hoje o Porteiro mede *extensão* da queda (ATR, Bollinger, EMA), mas não mede *força direcional* da queda. Duas quedas de −5% idênticas em extensão podem ser um fundo em formação (ADX baixo) ou um colapso em curso (ADX 40 subindo) — a estratégia atual não distingue.

#### 3. Squeeze de volatilidade (Bollinger × Keltner / TTM Squeeze)

- **O quê:** quando as Bandas de Bollinger contraem para dentro do Canal de Keltner (20 EMA, 1,5×ATR), a volatilidade está comprimida e um movimento direcional é iminente. Backtest em componentes do S&P 500 por 10 anos: a transição squeeze→fire antecedeu movimentos ≥ 2× o range médio diário em ~68% dos casos dentro de 5 barras.
- **Onde encaixa:** `get_enriched_data()` — Keltner é EMA + ATR, ambos já calculados; custo incremental zero de API.
- **Como (plano):** detectar `squeeze_on_15m`/`squeeze_on_1h` (BB dentro do Keltner). Uso planejado: queda aguda → lateralização com squeeze = exaustão vendedora comprimindo (contexto altista para a IA); e squeeze rompendo para baixo = veto de timing (o movimento ainda não terminou).
- **Por quê:** o gatilho atual de entrada é "tocou a banda inferior" — um evento pontual. O squeeze adiciona a dimensão *temporal*: distingue fundo que já consolidou (compressão) de fundo ainda em expansão de volatilidade.

#### 4. Hierarquia multi-timeframe formal (Triple Screen de Elder)

- **O quê:** método publicado desde 1986 (Alexander Elder): o timeframe maior define a *permissão* (tendência/regime), o intermediário define o *setup*, o menor define o *gatilho*. Referenciado e backtestado há mais de 30 anos.
- **Onde encaixa:** reorganização conceitual do `get_enriched_data()` e do filtro do Porteiro. A profit_gain já baixa 4h/1h/15m — mas hoje os três TFs viram campos soltos no payload, sem hierarquia: nada impede a IA de aprovar uma entrada com o 4h em colapso se o 15m estiver bonito.
- **Como (plano):** formalizar papéis — 4h: regime (RSI 4h + ADX 4h + SMA200 → permite/nega); 1h: setup (Bollinger + divergências + EMA); 15m: gatilho (candle de confirmação + volume). O Porteiro passa a exigir alinhamento em cascata; o payload da IA ganha um campo `timeframe_alignment` resumindo a cascata.
- **Por quê:** transforma dados que já existem em estrutura de decisão. Custo zero de API, ganho de coerência — e dá à IA um critério objetivo que hoje ela precisa inferir sozinha.

### Camada B — Gatilhos de entrada (refinamentos do Porteiro)

#### 5. RSI(2) de Larry Connors

- **O quê:** RSI de período 2 — extremamente sensível — para capturar o exato ponto de exaustão de curtíssimo prazo: abaixo de 10 = sobrevenda extrema. Publicado por Connors ("Short Term Trading Strategies That Work", 2008); backtests de décadas mostram win rate de 75–79% em ações/índices, e a premissa (reversão após extremos de curto prazo) é confirmada em múltiplos regimes de mercado.
- **Onde encaixa:** `get_enriched_data()` — uma linha a mais de `pandas_ta` sobre os klines 1h/15m já baixados.
- **Como (plano):** `rsi2_1h` e `rsi2_15m` no payload; regra planejada de timing: só liberar entrada quando RSI(2) 15m < 10 **e virando para cima** (valor atual > valor da vela anterior) — compra na virada, não na queda.
- **Por quê:** o RSI 14 atual diz que o ativo está esticado; o RSI(2) diz *quando* dentro da esticada. Resolve um problema real da estratégia: hoje ela pode comprar o toque na banda com o preço ainda descendo.

#### 6. Divergência altista de RSI (com confirmação de cruzamento do 50)

- **O quê:** preço faz mínima mais baixa, RSI faz mínima mais alta — a pressão vendedora esgota antes do preço. A evidência mostra: fraca isolada, forte com confirmação — a regra objetiva mais citada é o RSI cruzar de volta acima de 50 após a divergência, e a confiabilidade aumenta em timeframes maiores e após tendência prolongada (Kraken Learn, backtests da QuantifiedStrategies com variantes de RSI de curto prazo chegando a 91% de win rate).
- **Onde encaixa:** `get_enriched_data()` — a estratégia já calcula `rsi_1h_slope` (inclinação de 1 vela); a divergência é a versão estrutural disso, comparando os últimos N fundos.
- **Como (plano):** detectar nos últimos ~12 candles 1h: mínima de preço mais baixa + mínima de RSI mais alta → `rsi_bullish_divergence_1h: true`; confirmação `rsi_crossed_50: true/false`. Divergência confirmada = peso alto no payload; divergência sem confirmação = informação, não gatilho.
- **Por quê:** é o detector clássico de exaustão vendedora — exatamente a tese da estratégia ("Exaustão Vendedora confirmada", prompt da IA) — mas hoje a IA precisa *deduzir* divergência olhando o array de price action. Calcular explicitamente tira a inferência mais importante das mãos do LLM.

#### 7. IBS — Internal Bar Strength

- **O quê:** `(close − low) / (high − low)` — onde a vela fechou dentro do próprio range. IBS < 0,2 = fechamento colado na mínima → forte tendência estatística de reversão no período seguinte. Uma das técnicas com evidência mais consistente da pesquisa: paper no arXiv (ETFs de países), análises independentes (Alvarez Quant, Jonathan Kinlay) e backtests públicos — retorno médio de +0,35% no dia seguinte quando IBS < 0,20 vs −0,13% quando IBS > 0,80, efeito estável por mais de duas décadas.
- **Onde encaixa:** `get_enriched_data()` — cálculo trivial sobre a última vela 1h e diária, dados já baixados, custo zero.
- **Como (plano):** `ibs_1h` e `ibs_daily` no payload; uso como *desempate* de timing: entre duas candidatas aprovadas, priorizar a de menor IBS; e como gate leve (IBS diário < 0,3 favorece entrada).
- **Por quê:** é o indicador de reversão de melhor custo-benefício que existe — uma divisão por vela. Cobre um ângulo que nenhum indicador atual da estratégia cobre: a *posição do fechamento* dentro do range (o `bottom_rejection_1h` atual olha o pavio; o IBS quantifica o fechamento).

#### 8. Oscilador de exaustão secundário (Estocástico 20/80, com CCI como alternativa)

- **O quê:** Estocástico (K/D) abaixo de 20 com cruzamento de K acima de D = gatilho de reversão; CCI abaixo de −100 recuperando cumpre papel análogo. No backtest de 120 mil trades da Liberated Stock Trader sobre 5 indicadores de reversão, Estocástico e CCI ficaram entre os mais eficazes (junto com Bollinger, que a estratégia já usa).
- **Onde encaixa:** `get_enriched_data()` — `pandas_ta` tem ambos; mais uma linha sobre dados existentes.
- **Como (plano):** `stoch_k_15m`, `stoch_oversold_cross_15m` (K<20 e K cruzou D para cima) no payload, como voto de confluência — nunca gatilho isolado.
- **Por quê:** o funil atual depende de um único oscilador (RSI) para leitura de sobrevenda. Um segundo oscilador de família diferente (Estocástico usa posição no range de N períodos, não magnitude de ganhos/perdas) reduz o risco de ponto cego de um indicador só — e a literatura de confluência (item 15) mostra que exigir concordância entre famílias diferentes eleva o win rate.

#### 9. Padrões de candle de reversão COM confirmação (engolfo, martelo, piercing)

- **O quê:** a evidência acadêmica é explícita: padrões isolados não têm valor estatístico confiável (em cripto, um estudo com 68 padrões achou performance pior que aleatória na maioria), **mas** padrões específicos com confirmação e contexto mostram resultados significativos — Piercing significativo no mercado de Taiwan (ScienceDirect), Harami com 72,85% de acerto em estudo setorial (SSRN), e backtests de reversão à média no S&P mostram que adicionar confirmação de candle reduz drawdown vs entrada cega em sobrevenda.
- **Onde encaixa:** refinamento direto de campos que já existem: `bullish_1h_candle` e `bottom_rejection_1h` são versões informais de "candle de reversão". 
- **Como (plano):** substituir os dois booleanos por detecção nomeada (engolfo altista, martelo, piercing) **mais** a regra de confirmação da literatura: o padrão só vale se a vela seguinte fechar acima do fechamento do padrão. Campo planejado: `reversal_pattern_1h: "ENGULFING_CONFIRMED" | "HAMMER_UNCONFIRMED" | null`.
- **Por quê:** mantém o que a estratégia já acredita (price action de fundo) mas troca heurísticas caseiras por padrões com literatura e regra de confirmação — e entrega à IA um rótulo semântico em vez de dois booleanos crus.

#### 10. Divergência no histograma do MACD

- **O quê:** preço faz mínima mais baixa, histograma do MACD faz mínima mais alta — o momentum de baixa decai antes do preço virar. Estudo comparativo em cripto (2020–2022) documenta acurácia acima de 60% do MACD na identificação de reversões de tendência, e a divergência é a forma estruturalmente mais forte do sinal.
- **Onde encaixa:** `get_enriched_data()` — o MACD 1h já é calculado; hoje a estratégia extrai só `macd_1h_shifting_up` (comparação de 2 velas). 
- **Como (plano):** comparar os últimos 2 fundos do histograma vs os 2 fundos de preço correspondentes nos ~24 candles 1h; `macd_bullish_divergence_1h: true/false` no payload.
- **Por quê:** mesmo racional do item 6, aplicado ao indicador de momentum que a estratégia já considera central — `shifting_up` de 2 velas é ruidoso (qualquer respiro sobe o histograma); a divergência estrutural filtra esse ruído.

### Camada C — Preço justo, alvos e saída

#### 11. VWAP ancorada (AVWAP) com bandas de desvio

- **O quê:** o preço médio ponderado por volume desde uma âncora relevante (topo do swing que iniciou a queda, ou mínima das 24h) é o benchmark de execução institucional — bilhões em ordens são medidos contra VWAP diariamente. Pesquisa citada: ~63% de taxa de reversão a partir de extensões de 2 desvios-padrão da VWAP; backtests simples de reversão à VWAP em SPY mostram edge positivo de longo prazo.
- **Onde encaixa:** duas pontas — entrada (`get_enriched_data`: distância do preço à AVWAP em σ como métrica de esticada) e **saída** (bloco de monitoramento): a AVWAP ancorada no início da queda é um alvo de reversão *estrutural*, mais informativo que o gatilho fixo de +1,5% atual.
- **Como (plano):** calcular AVWAP sobre os klines 1h já baixados (âncora = topo mais alto das últimas 48h); payload ganha `avwap_distance_sigma`; na saída, planejar `target_price` como `min(AVWAP, buy_price × 1,015)` — realista quando a AVWAP está perto, agressivo quando está longe.
- **Por quê:** a estratégia hoje não tem noção de "preço justo" — entra no extremo e torce pelo +1,5%. A AVWAP dá o ponto de equilíbrio real do mercado desde o evento de queda, tornando alvo e esticada quantificados contra o volume real negociado.

#### 12. Volume Profile (POC, HVN, LVN)

- **O quê:** histograma de volume por *nível de preço* (não por tempo): POC = nível mais negociado ("preço justo" da distribuição, que atrai o preço); HVN = zonas de alto volume (suporte/resistência naturais); LVN = vácuos de liquidez (o preço os atravessa rápido). Ferramenta padrão institucional (material Schwab, OANDA, thinkorswim) com amplo consenso de praticantes.
- **Onde encaixa:** validação de fundo no Porteiro + definição de alvo na saída.
- **Como (plano):** construir um perfil aproximado com os klines 1h/15m já baixados (bins de preço × volume — sem chamadas extras): (a) entrada — `support_hvn_below: true/false`: fundo apoiado em HVN é fundo com demanda histórica; fundo caindo num LVN é vácuo (veto de timing); (b) saída — `poc_above_price`: POC acima do preço é alvo natural de reversão, combinável com a AVWAP do item 11.
- **Por quê:** todos os indicadores atuais da estratégia são derivados de *tempo* (candles sequenciais). O Volume Profile é o único que responde "NESTE preço, quanto o mercado já negociou?" — exatamente a pergunta que valida se um fundo tem chão.

### Camada D — Confirmação por fluxo e sentimento

#### 13. OBV (On-Balance Volume) e divergência de volume

- **O quê:** soma cumulativa de volume assinado pela direção do candle. Divergência altista (preço faz mínima mais baixa, OBV faz mínima mais alta) = acumulação durante a queda. Backtests públicos (QuantifiedStrategies, em SPY) mostram profit factors razoáveis; a literatura converge que OBV vale como *confirmação*, não como sinal isolado — e que funciona melhor em timeframes maiores.
- **Onde encaixa:** `get_enriched_data()` — cálculo trivial sobre closes e volumes 1h já baixados.
- **Como (plano):** `obv_bullish_divergence_1h: true/false` no payload, como voto de confluência; e no prompt da IA, instruir a cruzar com `volume_15m_pct` (que já existe): queda com OBV divergindo + volume subindo no fundo = assinatura clássica de absorção.
- **Por quê:** o único uso de volume hoje é "volume 15m ≥ 80% da média" — mede *atividade*, não *direção* do fluxo. O OBV adiciona a direção: distingue volume de capitulação/absorção (comprador entrando) de volume de distribuição (vendedor saindo).

#### 14. Funding rate + Open Interest (sentimento de derivativos)

- **O quê:** cripto-específico: funding rate negativo extremo (shorts pagando para manter posição) combinado com Open Interest caindo perto de suporte = capitulação — o padrão documentado dos grandes fundos (COVID mar/2020, FTX nov/2022: sequências longas de funding negativo precederam rallies relevantes; material educacional Kraken/Phemex/Gate documenta a mecânica).
- **Onde encaixa:** acréscimo novo — único item da lista que exige dados fora dos klines spot: endpoints públicos da Binance Futures (`premiumIndex`/`fundingRate`, `openInterest`), sem autenticação, 1–2 chamadas por candidata, cacheáveis (funding muda a cada 8h).
- **Como (plano):** `funding_rate_8h`, `funding_negative_streak` e `open_interest_trend` no payload da IA como camada de *sentimento*; regra planejada: funding muito negativo + OI caindo = reforço de fundo (capitulação); funding muito negativo + OI **subindo** = shorts agressivos ainda entrando (cautela). Sem veto duro — a IA pondera.
- **Por quê:** todos os dados atuais da estratégia vêm do gráfico spot — ela não enxerga o posicionamento do mercado. Em cripto, o mercado de perpétuos é onde a alavancagem (e a capitulação) acontece; é o dado de sentimento mais objetivo disponível de graça.

### Camada E — Meta-técnica

#### 15. Score de confluência ponderado (substituir o gate binário)

- **O quê:** a literatura comparativa é consistente: indicadores isolados acertam pouco acima de 50%; exigir concordância de um pequeno conjunto complementar eleva win rates para a faixa de 70% (estudos de RSI+MACD+Bollinger combinados em cripto; EMA+RSI 66,7% vs 59,1% do EMA sozinho). A forma madura disso não é um AND rígido, e sim um **score ponderado com threshold**.
- **Onde encaixa:** refatoração do coração do Porteiro (`scan_market`, filtro `bollinger_ok AND vol_ok AND ema_ok`) — e resolve de tabela um problema de comportamento já mapeado: o AND rígido zera candidatas na maioria dos ciclos e deixa o Tribunal de Swap (que exige 4 candidatas) praticamente inerte.
- **Como (plano):** cada técnica das camadas A–D vira um voto com peso (ex.: divergência RSI confirmada = 3; IBS < 0,2 = 2; squeeze = 1; OBV divergindo = 2; candle confirmado = 2; funding capitulando = 2…). Score ≥ X → candidata vai à IA **com o score e a lista de votos no payload**; a IA deixa de receber booleanos soltos e passa a receber um caso montado. Thresholds distintos: entrada normal (X), Tribunal de Swap (X+margem).
- **Por quê:** é a técnica que faz as outras 14 funcionarem juntas sem transformar o Porteiro num AND de 14 condições (que nunca dispararia). Gradua a qualidade do setup em vez de binarizá-la — e dá transparência total no dossiê da UI (quais votos a candidata teve).

---

## Descartadas na revisão (mitigação de técnicas fake/mal formadas)

| Técnica | Por que ficou de fora |
|---|---|
| **Fibonacci retracement** (níveis 38,2/61,8, "golden pocket") | Estudo empírico de 2022 (Dow, NASDAQ, DAX — ScienceDirect): probabilidade de reversão em nível de Fibonacci estatisticamente **indistinguível de níveis aleatórios**; estratégias baseadas nele subperformam o buy-and-hold. Só "funciona" quando coincide com suporte/volume reais — que os itens 11–12 já medem diretamente. |
| **Wyckoff Spring / "liquidity sweep" / SMC isolado** | Conceito coerente (falha de rompimento com reclaim), mas **sem backtests quantitativos robustos publicados** — a evidência é quase toda anedótica/praticante, e a própria literatura admite alta taxa de sinal falso fora de contexto de acumulação. O que ele tem de aproveitável (rejeição de fundo + volume) já é coberto pelos itens 9 e 13 com regras objetivas. |
| **Padrões de candle isolados** (sem confirmação) | Estudo com 68 padrões em criptomoedas: maioria performou **pior que aleatório**; outro estudo mostra perda de poder preditivo em regimes de crise. Entraram apenas na forma confirmada e contextualizada (item 9). |
| **Indicadores de período ultracurto sem contexto** (SMA de 1–3 períodos etc.) | Na análise de 100 mil+ backtests, as piores estratégias do dataset eram consistentemente as que usavam lookbacks curtíssimos — ruído puro gerando sinal constante. O RSI(2) do item 5 escapa disso porque tem regra de regime e confirmação de virada, não uso isolado. |

---

## Mapa-resumo: técnica × ponto da profit_gain

| # | Técnica | Ponto da estratégia | Tipo | Custo API |
|---|---|---|---|---|
| 1 | SMA200 diária (ativo + BTC) | Gate antes do Porteiro | Acréscimo | +1 klines/dia (cache) |
| 2 | ADX < 20–25 | Porteiro + payload | Acréscimo | Zero (klines existentes) |
| 3 | Squeeze BB×Keltner | Porteiro + payload | Acréscimo | Zero |
| 4 | Triple Screen (4h→1h→15m) | Estrutura do filtro | Refinamento | Zero |
| 5 | RSI(2) virando | Gatilho fino de entrada | Acréscimo | Zero |
| 6 | Divergência RSI + cross 50 | Porteiro + payload | Refinamento (do `rsi_1h_slope`) | Zero |
| 7 | IBS | Desempate/gate leve | Acréscimo | Zero |
| 8 | Estocástico/CCI | Voto de confluência | Acréscimo | Zero |
| 9 | Candles nomeados confirmados | Payload | Refinamento (de `bullish_1h_candle`/`bottom_rejection_1h`) | Zero |
| 10 | Divergência MACD | Payload | Refinamento (do `macd_1h_shifting_up`) | Zero |
| 11 | AVWAP + bandas σ | Entrada + alvo de saída | Acréscimo | Zero |
| 12 | Volume Profile (POC/HVN/LVN) | Validação de fundo + alvo | Acréscimo | Zero |
| 13 | OBV divergência | Voto de confluência | Acréscimo | Zero |
| 14 | Funding + Open Interest | Sentimento no payload | Acréscimo | +1–2 chamadas públicas (cache 8h) |
| 15 | Score de confluência | Coração do Porteiro | Refatoração | Zero |

Treze das quinze técnicas custam **zero chamadas extras de API** — são cálculo novo sobre klines que a estratégia já baixa.

## Sugestão de ordem de adoção (quando sair do planejamento)

1. **Fase 1 — regime e estrutura (defesa):** itens 1, 2, 4 — impedem a entrada no cenário errado.
2. **Fase 2 — score de confluência (fundação):** item 15 — cria o encaixe para todos os votos.
3. **Fase 3 — votos de entrada:** itens 5, 6, 7, 8, 9, 10, 3 — cada um entra como peso no score, testável individualmente.
4. **Fase 4 — preço justo e alvos:** itens 11, 12 — mudam também a saída, mexem com dinheiro real, ficam por último entre os on-chart.
5. **Fase 5 — sentimento externo:** itens 13, 14 — novos domínios de dado, adicionados quando o resto estiver estável.

---

## Fontes principais

- QuantifiedStrategies — [RSI 2 / Connors](https://www.quantifiedstrategies.com/rsi-2-strategy/), [RSI backtests](https://www.quantifiedstrategies.com/rsi-trading-strategy/), [IBS](https://www.quantifiedstrategies.com/ibs-internal-bar-strength-indicator-strategies/), [OBV](https://www.quantifiedstrategies.com/on-balance-volume-strategy/), [Triple Screen](https://www.quantifiedstrategies.com/alexander-elder-triple-screen-strategy/), [Mean reversion](https://www.quantifiedstrategies.com/mean-reversion-trading-strategy/)
- [Análise de 100.000+ backtests (Medium/Austin Starks)](https://medium.com/@austin-starks/i-analyzed-100-000-backtests-to-find-the-best-trading-indicator-42b31b739ff1)
- [Liberated Stock Trader — 120K trades, 5 indicadores de reversão](https://www.liberatedstocktrader.com/mean-reversion-trading-strategy/)
- IBS: [arXiv — Country ETFs](https://arxiv.org/pdf/2306.12434), [Alvarez Quant Trading](https://alvarezquanttrading.com/blog/internal-bar-strength-for-mean-reversion/), [Jonathan Kinlay](https://jonathankinlay.com/2019/07/the-internal-bar-strength-indicator/)
- Candlesticks: [ScienceDirect — Taiwan](https://www.sciencedirect.com/science/article/abs/pii/S1058330012000092), [SAGE — profitability](https://journals.sagepub.com/doi/pdf/10.1177/2158244017736799), [SSRN — NIFTY IT](https://papers.ssrn.com/sol3/Delivery.cfm/5755102.pdf?abstractid=5755102&mirid=1), [regimes de mercado](https://www.sciencepublishinggroup.com/article/10.11648/j.im.20260101.16)
- Fibonacci (descarte): [ScienceDirect — avaliação empírica](https://www.sciencedirect.com/science/article/abs/pii/S0957417421012495), [forexop — fact or fiction](https://forexop.com/strategy/fibonacci-fact-or-fiction/)
- ADX: [Fidelity](https://www.fidelity.com/viewpoints/active-investor/average-directional-index-ADX), [Schwab](https://www.schwab.com/learn/story/spot-and-stick-to-trends-with-adx-and-rsi), [StatOasis](https://statoasis.com/post/how-to-use-the-adx-indicator-like-a-pro-step-by-step-guide)
- VWAP/AVWAP: [TrendSpider](https://trendspider.com/learning-center/anchored-vwap-trading-strategies/), [TradeAlgo](https://www.tradealgo.com/trading-guides/technical-analysis/vwap-trading-strategy-the-institutional-benchmark-every-trader-should-know), [CrossTrade — VWAP reversion](https://crosstrade.io/learn/trading-strategies/vwap-reversion)
- Volume Profile: [Schwab](https://www.schwab.com/learn/story/using-volume-profile-indicator), [OANDA](https://www.oanda.com/us-en/trade-tap-blog/trading-knowledge/volume-profile-explained/), [Optimus Futures — POC](https://optimusfutures.com/blog/point-of-control-explained-the-most-important-level-on-volume-profile-futurestrading-daytrading/)
- Squeeze: [StockCharts — TTM Squeeze](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ttm-squeeze), [Volatility Box — backtests](https://volatilitybox.com/research/ttm-squeeze-indicator/)
- RSI divergência: [Kraken Learn](https://www.kraken.com/learn/rsi-divergences-what-they-how-they-work), [Pembe.io — backtesting](https://www.pembe.io/blog/rsi-divergence-backtest)
- Funding/OI: [Kraken — funding como sinal](https://www.kraken.com/learn/futures-trading-funding-rate-strategy), [Phemex — 46 dias negativos/FTX](https://phemex.com/blogs/bitcoin-funding-rates-negative-46-days-ftx-bottom), [Zipmex — guia](https://zipmex.com/blog/how-to-analyze-funding-rates-in-crypto/)
- MACD em cripto: [ResearchGate — RSI vs MACD 2020–2022](https://www.researchgate.net/publication/377921778_a-comparative-study-between-rsi-and-macd-to-predict-opportunities-in-cryptocurrency-market-from-2020-to-2022_1)
- Confluência: [ResearchGate — RSI+Bollinger effectiveness](https://www.researchgate.net/publication/392316831_Effectiveness_of_RSI_and_Bollinger_Bands_in_Identifying_Buy_and_Sell_Signals), [newtrading.io — estudo indicadores](https://www.newtrading.io/best-technical-indicators/)
- Wyckoff Spring (descarte do uso isolado): [Trading Wyckoff — Spring & Shakeout](https://tradingwyckoff.com/en/spring-shakeout/), [JISEM — Wyckoff Theory](https://www.jisem-journal.com/download/60_Wyckoff%20Theory.pdf)
