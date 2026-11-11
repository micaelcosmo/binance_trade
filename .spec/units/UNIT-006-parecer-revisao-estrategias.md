# UNIT-006 · Pesquisa · parecer de revisão das estratégias de trade

- **Status:** Implemented
- **Épico/fase:** Pesquisa/análise (insumo de E2/E4 e ADR-0009) · **Prioridade:** —
- **ADRs:** ADR-0002, ADR-0009
- **Arquitetura:** `arch.yaml#strategies`, `#known_issues` (STRAT-01..09)
- **Origem:** `.spec/strategies/000-parecer-revisao-estrategias.md` (migrado integralmente em 2026-11-11, épico E1)

> **Situação atual:** Documento de análise entregue (2026-07-19), aguardando revisão do Micael. Texto integral abaixo. Correção ao ler o código atual: o clamp do stop dinâmico para BTC é **6–10,5%** (não 4–10,5%); o multiplicador é 4×ATR% (1h). Números de linha citados podem ter se deslocado.

<details><summary>Metadados originais</summary>

Título original: `000 — Parecer: Estratégias de Trade`

- **Data:** 2026-07-19
- **Escopo:** `binance_trade_bot/strategies/` — o que cada estratégia faz e como está o comportamento dela.

</details>

---

## 1. profit_gain_strategy.py (motor principal)

### O que ela faz

Estratégia de **reversão à média** em duas camadas:

1. **Filtro matemático (o "Porteiro"):** a cada ciclo de scout, varre todas as moedas da lista e calcula indicadores em 3 tempos gráficos (4h, 1h, 15m): RSI, EMA 9/21, MACD, ATR e Bandas de Bollinger. Só considera candidata a moeda que teve queda aguda validada pelo ATR (`min_24h_change <= -2×ATR%`), tocou a banda inferior de Bollinger (15m ou 1h), tem volume 15m ≥ 80% da média e está esticada abaixo da EMA21 (< −1%).
2. **Auditoria da IA (Gemini):** as candidatas que passam no filtro vão em lote para a IA, que analisa price action de 12h, momentum (MACD) e contexto de fundo. Só compra se a IA devolver uma vencedora com confiança ≥ 90%.

**Entrada:** market order com ~99% do saldo livre em USDT (all-in).
**Saída:** três gatilhos — trailing stop invisível (ativa em +1,5%, vende se recuar 0,3% do pico), stop loss dinâmico calculado pelo ATR da moeda (clamp 4–10,5% para BTC, 4–`base_stop_loss_pct` para alts) e disaster stop fixo (−15%).
**Tribunal de Swap:** se a posição ficar ≥ 10h presa em prejuízo leve (entre −0,15% e −2,5%), a IA avalia migrar para outra candidata — exige confiança ≥ 95% e pelo menos 4 candidatas no lote.
**Disciplina diária:** hiberna até a meia-noite ao bater a meta de lucro diário ou o limite de trades.
**Estado:** persiste operação, placar e histórico em `profit_gain_state.json`; aceita comandos da UI via flags (venda forçada, ajuste de cooldown, desvio do Bollinger, +1 trade, reset de placar).

### Como está o comportamento

**Pontos fortes:**
- O funil matemática → IA é coerente: a IA nunca decide sozinha, só ratifica candidatas que já passaram por critérios objetivos, e o veredito dela ainda passa por normalização antes de ser aceito.
- Gestão de saída em camadas (trailing + stop ATR + disaster) é bem desenhada e adaptativa por moeda.
- A hibernação diária e o cooldown do motor impõem disciplina real — o bot não fica overtrading.
- Recuperação de estado após restart: retoma a operação em andamento, recupera preço de compra real via histórico de trades quando não o tem.

**Problemas de comportamento:**

1. **Toda a proteção é por software.** O trailing é invisível de propósito e os stops só disparam dentro do `scout()`. Se o processo cair ou perder rede, a posição fica sem nenhuma proteção na corretora — o disaster stop de −15% só existe enquanto o bot está vivo.
2. **O stop reage devagar quando em operação.** O `scan_market()` executa a mineração completa do mercado (várias chamadas de klines por moeda) **antes** de checar o preço da posição. Com scout a cada 60s + duração da varredura, uma queda rápida pode atravessar o stop dinâmico e ser vendida bem abaixo do nível planejado ([profit_gain_strategy.py:619-657](../../binance_trade_bot/strategies/profit_gain_strategy.py#L619-L657) roda antes de [linha 691+](../../binance_trade_bot/strategies/profit_gain_strategy.py#L691)).
3. **O preço de compra gravado não é o preço executado.** `active_buy_price` recebe o preço observado no scan, não o fill real do market order ([profit_gain_strategy.py:567](../../binance_trade_bot/strategies/profit_gain_strategy.py#L567)). Todo o P/L, trailing e stop herdam o erro de slippage da entrada.
4. **A recuperação de estado assume qualquer moeda da carteira.** Com USDT < $5, o bot toma controle da primeira moeda com valor ≥ $5 na conta ([profit_gain_strategy.py:671-689](../../binance_trade_bot/strategies/profit_gain_strategy.py#L671-L689)) — inclusive uma que o bot nunca comprou, que passa a ser vendável pelos stops.
5. **O Tribunal de Swap quase nunca convoca.** Exige 4 candidatas passando o filtro estrito **ao mesmo tempo** ([linha 853](../../binance_trade_bot/strategies/profit_gain_strategy.py#L853)) — sendo que na maioria dos ciclos o filtro não aprova nenhuma. Na prática a funcionalidade tende a ficar inerte; e quando há menos de 4, o relógio do Tribunal é adiado em +45 min. Verificar se a intenção era ≥ 1.
6. **O cooldown do motor não economiza o que promete.** O check de `ai_cooldown_until` está depois do loop de mineração ([linhas 918-921](../../binance_trade_bot/strategies/profit_gain_strategy.py#L918-L921)) — durante o cooldown a varredura pesada continua rodando a cada scout; só a chamada à IA é poupada.
7. **O lucro diário soma percentuais por trade** (`daily_profit_pct += drop_percentage`) — não é o retorno real do dia (não compõe e ignora variação de capital entre trades). A meta de 5% e a hibernação disparam sobre um número aproximado.
8. **All-in não configurável:** 99% do saldo em toda entrada. Com stop de 4–10%, o risco por trade é 4–10% do capital total. Coerente com o perfil agressivo declarado, mas hoje é comportamento fixo, não escolha.
9. **Detalhe morto:** `maximum_hold_time_seconds = 7200` é definido e nunca usado — não existe timeout de posição; o hold só é limitado pelo Tribunal (≥ 10h).

---

## 2. default_strategy.py (legada)

### O que ela faz

Estratégia de **rotação entre altcoins** ("coin jumping"): mantém sempre uma moeda e pula para outra quando a razão de preços entre elas fica favorável descontando taxas (`_jump_to_best_coin` herdado). Sobre essa base, adiciona:

- **Regra de ouro / momentum:** só entra ou pula para moeda com alta ≥ 2% nas 24h.
- **Modo sobrevivência:** se o BTC cai ≤ −2,5% nas 24h, para de comprar e segura o que tem; volta ao normal quando o BTC recupera (≥ −0,5%).
- **Take profit global com trailing:** monitora o valor total (USDT + moeda atual) contra um saldo-base; quando o lucro passa de +3,5%, arma trailing e vende tudo para USDT se recuar 0,4% do pico, recomeçando o ciclo com o novo saldo (compounding).
- **Timeout:** se ficar ≥ 120 min na mesma moeda, força venda para USDT e volta a caçar.
- **Cooldown:** moeda vendida vai para "geladeira" por 60 min.

### Como está o comportamento

**Pontos fortes:**
- O modo sobrevivência do BTC é um circuit-breaker simples e eficaz para o comportamento de jump (evita rotacionar em mercado derretendo).
- O trailing global com compounding dá à estratégia um objetivo de saída claro, coisa que o coin-jumping puro não tem.

**Problemas de comportamento:**

1. **A base do lucro global zera a cada restart.** `initial_global_balance` e `peak_profit_perc` vivem só em memória: reiniciou o bot, o +3,5% passa a contar do saldo atual e o pico do trailing some. Depósitos/saques na conta também entram no cálculo — um depósito vira "lucro" instantâneo e pode disparar a venda.
2. **O timeout vende no prejuízo por relógio.** Aos 120 min, vende a mercado sem olhar P/L e sem registrar o resultado em lugar nenhum — o custo dessa regra é invisível no comportamento observável do bot.
3. **Sem stop loss.** Fora do trailing global (que só age no lucro) e do timeout, não há corte de perda por posição — no modo sobrevivência o bot segura a moeda em queda indefinidamente ("Timeout cancelado").
4. **Quando o preço da moeda atual falha, o ciclo aborta cedo** (`if current_coin_price == 0.0: return`, [default_strategy.py:172](../../binance_trade_bot/strategies/default_strategy.py#L172)) — naquele tick nada é reavaliado, nem o status é atualizado.
5. **`bridge_scout()` sobrescrito é cópia do herdado** ([linhas 220-240](../../binance_trade_bot/strategies/default_strategy.py#L220-L240)) — mesmo comportamento, código duplicado.

---

## 3. multiple_coins_strategy.py (upstream)

### O que ela faz

Variação do coin-jumping original: em vez de uma moeda única "atual", itera **todas** as moedas com saldo relevante (≥ min notional) e tenta o jump de cada uma independentemente. Sem saldo em nenhuma, faz o `bridge_scout` padrão. A ideia é diluir o risco de ficar preso num único ativo em correção.

### Como está o comportamento

- É o código original do projeto upstream, intocado. Herda a regra de ouro e cooldowns do `AutoTrader`, mas não tem nenhum dos refinamentos das outras (sem take profit, sem trailing, sem proteção de BTC, sem timeout, sem stop).
- Status só no console (`print` com `\r`); não produz o `bot_status.json` que as outras produzem — rodando ela, o painel não vê nada.
- Comportamento em si é consistente com a proposta (diluição primária de risco), mas está defasada em relação ao resto do ecossistema. Vale decidir: aposentar ou atualizar.

---

## 4. Conclusão

| | profit_gain | default | multiple_coins |
|---|---|---|---|
| Tese | Reversão à média + IA | Rotação com momentum | Rotação diluída |
| Entrada | Filtro ATR/Bollinger/volume/EMA + IA ≥ 90% | Razão de preços + alta 24h ≥ 2% | Razão de preços |
| Saída | Trailing 1,5/0,3 + stop ATR + desastre 15% | Trailing global 3,5/0,4 + timeout 120min | Só jump |
| Stop loss | Sim (software) | Não | Não |
| Estado persistente | Sim | Não (base zera no restart) | Não |
| Avaliação | Madura, 4 pontos críticos de execução | Funcional, frágil no restart e sem stop | Defasada |

A `profit_gain` é a única com gestão de risco completa e é onde vale concentrar evolução — os pontos 1 a 4 dela (stop só em software, latência do stop, preço de compra sem fill real, sequestro de carteira na recuperação) são os que mexem com dinheiro real e mereceriam correção antes de qualquer feature nova. A `default` funciona como legada, mas o comportamento do lucro global depende do processo nunca reiniciar. A `multiple_coins` está órfã do ecossistema atual.
