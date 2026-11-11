# sim-002 — Variações estruturais de saída, entrada e custos (T-024, épico E2)

- **Data:** 2026-11-11 · **Agente:** ag-sim
- **Código:** `simulation/run_sim002.py`. O motor foi estendido em `simulation/engine.py` com:
  - stop fixo;
  - breakeven;
  - saída parcial;
  - time-stop;
  - confirmação de entrada;
  - entrada limit/maker.
- **CSVs:** `sim-002-grid.csv`, `sim-002-por-moeda.csv`, `sim-002-robustez.csv` e `sim-002-params.json`.

## Resposta direta

**Não.** Nenhuma das 89 configurações teve expectância líquida positiva e robusta ao mesmo tempo em IS **e** OOS **e** sob latência ou slippage pior.

O que mais se aproximou foi a melhor execução escolhida pelo IS (`limit −0,6% válida por 4 velas`) com a taxa BNB de 0,075%. Ela fica levemente positiva só no cenário otimista: carteira IS **+0,05% por trade** (+0,6% no período). Mesmo assim, a carteira OOS fica em −0,14%. Com checagem só no fechamento de 15m, cai para −0,19% (IS) e −0,52% (OOS).

**As saídas com R:R explícito (stop apertado e alvo maior) pioram tudo.** Todas as 38 variações de saída (grupos A–D) ficaram abaixo da referência no IS. Stops de 1,5–3% são atingidos pelo ruído logo depois da entrada. Num setup de reversão à média, comprado no fundo esticado, o win rate cai de 78% para 21–65%. Os poucos que chegam ao alvo maior não compensam essa queda.

## Metodologia (igual à sim-001)

- **Dados:** 11 moedas USDT, de 15/07/2024 a 01/11/2026.
- **Split:**
  - IS de 15/07/2024 a 22/02/2026;
  - OOS de 22/02/2026 a 01/11/2026.
- **Seleção:**
  - Feita só no IS.
  - Score SQN pooled por moeda, com penalidade para menos de 30 trades e para moedas negativas.
  - Rebaixamento se a carteira IS for negativa.
- **Modos:**
  - carteira, fiel ao live: uma posição por vez, all-in;
  - por moeda.
- **Gate SMA200 diária do ativo ligado em todas as variações** (novo default do live).
- **REF:** a configuração atual com o gate SMA200.
  - A REF reproduz exatamente a `sma200=asset` da sim-001: 390 trades e −41,04% na carteira IS.
  - Isso é a regressão de que a extensão do motor não mudou o comportamento antigo.
- **Execução padrão:** stop intra-vela em pior caso, taxa de 0,1% por lado e slippage de 0,05%.
- **Checagens de robustez** (REF e top-6 do score IS): `@close` (latência), `@slip0.2`, `@close+slip0.2` e `@fee0.075`.
- **Modelagem conservadora das novidades:**
  - **Limit/maker:**
    - O limite fica em `close do scan × (1 − offset)`, válido por N velas de 15m.
    - Só executa se a mínima **atravessar** o limite em 0,05%.
    - Fill no limite, sem slippage.
    - Na vela do fill só se checa o stop: se a mesma mínima que comprou também bateu o stop, sai no stop. A alta dessa vela é ignorada.
    - Se não executar, a ordem é cancelada e o motor volta a escanear.
  - **Parcial:** vende a fração no alvo 1, por caminho intra-vela. O stop tem prioridade se cair na mesma vela.
  - **Breakeven:** quando o pico chega a +X%, o stop vai para +0,2%, o que cobre as taxas.
  - **Time-stop:** depois de N horas, sai na abertura se o pico ainda estiver abaixo de +0,5%.
  - **Confirmação:** entra na vela k se houve sinal do Porteiro nas N velas anteriores **e** k fechou acima da máxima anterior (`brk`) ou acima da EMA9 15m (`ema9`).

## Grade: 53 no estágio 1, 2 no estágio 2 e 34 checagens, total de 89

| Grupo | Variações |
|---|---|
| A — R:R | stop fixo 1,5 / 2 / 3% × trailing 1,5/0,3, 2/0,5, 3/1, 5/1,5; stop ATR×1,5–2 com clamp 1,5–3%; trailing 2–5% com o stop atual; TP fixo com R:R 1:2 |
| B — breakeven | BE em +1% e +1,5%, isolado e combinado com stop apertado e trailing maior |
| C — parcial | 50% em +1,5% ou +2% e o resto em trailing 3/1 ou 4/1, com e sem BE depois da parcial |
| D — time-stop | 6, 12 e 24h, e 12h combinado com stop de 2% e trailing 3/1 |
| E — confirmação | rompimento da máxima em 2, 4 ou 8 velas; fechamento acima da EMA9 em 4 ou 8 velas; combinações |
| F — custos/execução | taxa BNB 0,075%; slippage de 0,2%; limit −0 / −0,3 / −0,6% válida por 2 ou 4 velas; limit com taxa BNB |

Estágio 2:
- Nenhuma saída (A–D) bateu a REF no IS. Por isso as combinações ficaram restritas à melhor entrada × melhor execução, mais a melhor execução com taxa BNB.
- A primeira execução gerou um estágio 2 vazio por causa desse caso.
- Corrigi `combos()` e rodei o suplemento com a mesma lógica.

## Tabela principal (expectância líquida por trade; carteira = n trades e retorno composto)

| Variação | Carteira IS | Carteira OOS | Por moeda IS | Por moeda OOS (moedas +) | Carteira IS @close | Carteira OOS @close | Carteira IS @slip0,2 | Carteira OOS @slip0,2 |
|---|---|---|---|---|---|---|---|---|
| **REF** (atual + SMA200) | −0,09% (390; −41,0%) | −0,24% (59; −15,0%) | −0,20% | −0,13% (5/11) | −0,35% | −0,64% | −0,39% | −0,53% |
| F: taxa BNB 0,075% | −0,04% (390; −28,5%) | −0,19% (59; −12,5%) | −0,15% | −0,08% (5/11) | −0,30% | −0,60% | −0,34% | −0,48% |
| **F: limit −0,6% ×4 velas** (top-1 IS) | −0,00% (318; −14,1%) | −0,19% (46; −9,9%) | −0,11% | −0,02% (5/11) | −0,24% | −0,57% | −0,15% | −0,34% |
| **S2: limit −0,6% ×4 + taxa BNB** | **+0,05% (318; +0,6%)** | −0,14% (46; −7,8%) | −0,06% | +0,03% (5/11) | −0,19% | −0,52% | −0,10% | −0,29% |
| E: fechamento > EMA9 em até 4 velas (top-2 IS) | −0,21% (345; −59,0%) | −0,11% (52; −7,4%) | −0,18% | −0,02% (7/11) | −0,26% | −0,45% | −0,51% | −0,41% |
| S2: EMA9 ×4 + limit −0,6% ×4 | −0,14% (261; −38,8%) | −0,25% (44; −12,3%) | −0,19% | −0,09% (5/11) | −0,40% | −0,82% | −0,29% | −0,40% |
| D: time-stop 12h | −0,15% (439; −56,5%) | −0,16% (75; −13,3%) | −0,20% | −0,15% (5/11) | — | — | — | — |
| B: breakeven em +1% | −0,17% (499; −63,7%) | −0,31% (76; −22,8%) | −0,23% | −0,14% (4/11) | — | — | — | — |
| C: 50% em +1,5%, resto trailing 3/1, BE | −0,27% (377; −68,6%) | −0,38% (48; −18,0%) | −0,39% | −0,21% (4/11) | — | — | — | — |
| A: stop 2% + trailing 3/1 (R:R ~1:1,5) | −0,33% (468; −81,2%) | −0,57% (64; −31,6%) | −0,37% | −0,20% (3/11) | — | — | — | — |
| A: trailing 3/1 com o stop atual | −0,54% (239; −77,3%) | −0,33% (27; −10,3%) | −0,50% | −0,09% (5/11) | — | — | — | — |
| A: stop 1,5% + TP 3% (R:R 1:2) | −0,36% (581; −88,8%) | −0,70% (88; −46,6%) | −0,37% | −0,34% | — | — | — | — |

Nota: o stop fixo e o TP sozinhos passaram longe do top-6, por isso não têm checagem de robustez (—). Eles já perdem no cenário otimista.

## Leitura

1. **A assimetria é o preço do win rate, não um defeito isolado.**
   - A REF ganha em 78% dos trades porque o stop largo (4–7%) aguenta o ruído depois de comprar uma faca caindo.
   - Com stop de 2%, 61% dos trades saem no stop (win rate 38%).
   - Com breakeven em +1%, metade dos trades sai no zero a zero (win rate 50%).
   - Em nenhum caso a cauda direita, que é o que o trailing maior captura, compensou.
   - Conclusão: o setup não tem momentum suficiente depois do toque na banda para sustentar R:R ≥ 1.
2. **A confirmação de entrada não ajudou de forma robusta.**
   - "Fechamento acima da EMA9" melhora o OOS por moeda (−0,02%, 7/11 moedas positivas), mas o IS fica igual ou pior que a REF.
   - O rompimento da máxima anterior piora: entra mais caro, com o mesmo stop.
3. **O único ganho real vem do custo e do preço de entrada.**
   - Limit 0,6% abaixo do scan, válida por 1h, mais taxa BNB, tira ~0,14 p.p. por trade. Isso leva ao empate.
   - Parte desse ganho é **seleção adversa favorável**: só executa quando o preço desce mais 0,6%, ou seja, uma entrada mais fundo. Isso equivale a mexer no Porteiro, e não é só economia de custo.
   - É também o ponto mais sensível ao modelo de fill. Na vida real, ordens maker em queda rápida podem ficar sem executar ou executar exatamente no pior momento.
4. **Latência continua matando.** Com checagem no fechamento de 15m, todas as configurações ficam com expectância entre −0,19% e −0,82% na carteira. O live (scout ~60 s mais a varredura antes do stop) fica entre os dois modos.

## Riscos e limitações

- **OOS curto:** o gate SMA200 deixa ~45–60 trades na carteira OOS (a baixa de 2026 fica toda de fora). Diferenças de ±0,1 p.p. estão no ruído.
- **A limit é a variação mais otimista do modelo.** O fill exige a mínima atravessar o limite em 0,05%, mas não modela a fila do book nem falha de API. Não há dados de book para calibrar isso.
- **O suplemento do estágio 2 (S2) foi rodado por um script à parte** com a mesma lógica de `combos()` (já corrigida). O par "limit + taxa BNB" é a junção de uma premissa de custo com a melhor execução do IS, não um parâmetro otimizado.
- **Mesmas limitações da sim-001:**
  - o Gemini não é simulado (oráculo aprovando tudo);
  - os indicadores usam só velas fechadas;
  - o Tribunal de Swap não é simulado.

## Recomendação

| Item | Recomendação | Classe |
|---|---|---|
| Stops apertados fixos ou ATR, R:R explícito, TP fixo, parcial, breakeven, time-stop | **Não adotar.** Todos piores que a REF no IS e no OOS | — |
| Confirmação por rompimento da máxima | **Não adotar** | — |
| Confirmação "fechamento > EMA9 15m em até 4 velas" | Não adotar agora. Só o OOS melhorou; reavaliar se a IA real entrar em shadow-mode | — |
| Taxa BNB (0,075%/lado) | **Ativar.** Ganho direto de ~0,05 p.p. por trade, sem efeito colateral | **Seguro** (é configuração da conta: D-202 da sim-001) |
| Entrada limit −0,6% válida por 4 velas (1h) | Só depois de um teste em paper/shadow medindo a taxa real de fill. No modelo é a única melhora relevante, mas é a mais dependente das premissas | **Decisão do Micael (D-210)** |
| Operar all-in com dinheiro real | Mesmo com o gate SMA200, BNB e limit, o melhor caso é empate e piora sob latência. **Não há configuração robusta e lucrativa** nesta família de estratégia | **Decisão do Micael (D-211)** |

## Decisões registradas

- **D-210 — Entrada limit/maker.** Opções:
  - (A) implementar a limit −0,6% por 1h em shadow/paper e medir o fill real;
  - (B) não implementar.
  - **Recomendação: A, só em paper.**
- **D-211 — Futuro da profit_gain.** Duas rodadas de simulação (190 configurações) não acharam edge líquido robusto. Opções:
  - (A) manter o live com tamanho mínimo e coletar dados da IA em shadow-mode;
  - (B) pausar o live;
  - (C) abrir uma spec de nova tese de entrada, já que o problema está no sinal (edge bruto ≈ custo), não na saída.
  - **Recomendação: A + C.**
