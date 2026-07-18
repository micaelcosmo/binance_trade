# 002 · Validação Rígida da Saída da IA (Gemini) + Fallback Seguro

> **Status:** Draft · **Prioridade:** P1 · **Fase:** A (Blindagem)
> **Depende de:** — · **Relaciona:** contrato `state-and-flags.md`
> **Issue coberta:** `AI-01` (saída da IA confiada sem schema rígido)
> **Princípio:** a IA é um **conselheiro não-confiável**. Sua saída entra num caminho que move **capital real** — nenhum campo dela pode ser usado sem validação. Em dúvida, **vetar** (`NENHUMA`/`HOLD`).

---

## 1. Contexto e motivação

`models/ai_agent.py` chama o Gemini e faz `json.loads(response.text)` **direto**, retornando o dict cru para a estratégia. Hoje:

```yaml
estado_atual:
  analyze_batch:
    where: "ai_agent.py:119"
    code:  "return json.loads(response.text)"
    expects: [winning_coin, final_confidence, decision_summary]
  analyze_swap:
    where: "ai_agent.py:163"
    code:  "return json.loads(response.text)"
  erro_handling:
    - "json.loads que lança exceção É capturado → retorna ERROR_503 (bom)"
    - "MAS: JSON válido com chaves faltando/tipos errados/valores absurdos passa direto (ruim)"
```

### Como a estratégia consome (superfície de risco)

```yaml
consumo_em_profit_gain_strategy:
  compra:   # scan_market ~ linha 926-960
    - "winning_coin = analysis.get('winning_coin','NENHUMA')"
    - "if winning_coin == 'ERROR_503' -> cooldown 5min"
    - "final_confidence = analysis.get('final_confidence',0)"
    - "if winning_coin != 'NENHUMA' and final_confidence >= 90 -> COMPRA"
    - "chosen = next(item in batch if item.coin == winning_coin, None)"
  swap:     # ~ linha 855-907
    - "winning_coin >= 95 e not in [HOLD,NENHUMA] -> vende atual + compra candidata"
riscos_reais:
  - id: AI-01a
    risk: "final_confidence como string ('95') => comparação '95' >= 90 lança TypeError em runtime"
  - id: AI-01b
    risk: "winning_coin inventada (não está no batch) => next()=None; hoje é tolerado, mas mascara alucinação"
  - id: AI-01c
    risk: "winning_coin com formatação suja ('btc', 'BTCUSDT', ' BTC ') => não casa com o batch e perde trade válido OU casa errado"
  - id: AI-01d
    risk: "final_confidence fora de faixa (120, -5, 9000) => decisão com base em número absurdo"
  - id: AI-01e
    risk: "decision_summary ausente => .splitlines()[0] lança IndexError"
  - id: AI-01f
    risk: "JSON válido mas vazio {} ou null => .get com default ajuda, mas estado inconsistente"
  - id: AI-01g
    risk: "resposta com cerca markdown (```json) apesar de response_mime_type => json.loads falha => ERROR_503 (degrada, não quebra)"
  - id: AI-01h
    risk: "campos extras/inesperados => ignorados hoje; ok, mas sem registro"
```

---

## 2. Objetivo

Inserir uma **camada de validação/normalização** entre `json.loads(...)` e o `return` dos métodos do `MarketAnalyzer`, de modo que a estratégia **sempre** receba um objeto com forma e valores garantidos — ou um veto seguro.

### Não-objetivos
- Mudar os prompts ou o modelo (`gemini-2.5-flash`) — fora do escopo.
- Alterar os limiares de decisão (90%/95%) — vivem na estratégia, intocados.
- Refatorar a estratégia (spec 005).

---

## 3. Contrato de saída normalizado (alvo)

Todo método do `MarketAnalyzer` retorna **estritamente** este shape:

```yaml
ai_verdict:
  winning_coin:      str    # ticker normalizado presente no batch, OU "NENHUMA"/"HOLD"/"ERROR_503"
  final_confidence:  int    # inteiro clampeado em [0, 100]
  decision_summary:  str    # sempre não-vazio (fallback textual se ausente)
sentinels:
  NENHUMA:   "nenhuma candidata aprovada (analyze_batch)"
  HOLD:      "manter posição atual (analyze_swap)"
  ERROR_503: "falha de comunicação/parse/validação — tratar como veto + cooldown"
garantias:
  - "final_confidence é SEMPRE int em [0,100]; nunca string, None, NaN ou fora de faixa"
  - "winning_coin é SEMPRE str; se for ticker, GARANTIDAMENTE existe no batch submetido"
  - "decision_summary é SEMPRE str com pelo menos 1 caractere útil"
```

---

## 4. Regras de validação/normalização

```yaml
validation_pipeline:   # aplicado à saída de json.loads, por método
  step_0_parse_guard:
    - "se json.loads falhar (já hoje) => ERROR_503 (mantém)"
    - "se resultado não for dict => ERROR_503"
  step_1_winning_coin:
    - "coerce para str; strip(); upper()"
    - "remover sufixo da base se presente (ex.: 'BTCUSDT' -> 'BTC')"
    - "se valor ∈ {NENHUMA, HOLD, ERROR_503} (case-insensitive) => manter sentinela canônica"
    - "senão, exigir que o ticker exista no conjunto de coins do batch:"
    - "   - presente  => aceitar normalizado"
    - "   - ausente   => AI-01b: rebaixar para NENHUMA/HOLD + auditar 'alucinacao_de_ticker'"
  step_2_confidence:
    - "aceitar int|float|str-numérica; coerce p/ float; arredondar p/ int"
    - "se não-numérico/NaN/inf => 0"
    - "clamp [0,100]"
  step_3_summary:
    - "coerce para str; se vazio/ausente => texto padrão 'Sem parecer fornecido pela IA.'"
    - "truncar comprimento máx. (ex.: 4000 chars) p/ proteger UI/log"
  step_4_consistency:
    - "se winning_coin é sentinela de veto (NENHUMA/HOLD/ERROR_503) => forçar final_confidence=0"
    - "(impede 'NENHUMA' com 95% acidental disparar lógica downstream)"
  step_5_audit:
    - "registrar qualquer correção aplicada (tipo coerrado, ticker alucinado, clamp) sem vazar a chave da API"
fallback_seguro:
  on_any_validation_error: '{ winning_coin: "ERROR_503", final_confidence: 0, decision_summary: "Saída da IA inválida; veto por segurança." }'
  filosofia: "falha fecha (fail-closed): erro NUNCA vira compra."
```

### Por que `fail-closed` é correto aqui
A estratégia só compra com `confidence >= 90` **e** ticker válido. Garantindo `ERROR_503`/`NENHUMA`/`HOLD` + `confidence=0` em qualquer anomalia, **nenhum** caminho de validação inválida consegue abrir/trocar posição. O pior caso vira "perdeu uma entrada", nunca "entrou errado".

---

## 5. Design da implementação

```yaml
where:
  file: binance_trade_bot/models/ai_agent.py
  approach: "função pura _normalize_verdict(raw, batch_coins, mode) chamada antes de cada return"
signature: |
  def _normalize_verdict(self, raw, batch_coins, mode):
      # raw: dict|qualquer (saída de json.loads)
      # batch_coins: set[str] dos tickers submetidos (normalizados)
      # mode: 'batch' (veto=NENHUMA) | 'swap' (veto=HOLD)
      # retorna: dict no shape da seção 3 (sempre)
integration:
  - "analyze_batch: batch_coins = {a['coin'].upper() for a in clean_batch}; mode='batch'"
  - "analyze_swap:  mesmo, mode='swap'"
  - "substituir 'return json.loads(response.text)' por:"
  - "   raw = json.loads(response.text); return self._normalize_verdict(raw, coins, mode)"
  - "manter o try/except externo (parse/IO) retornando ERROR_503"
notes:
  - "função PURA e determinística => trivial de testar (spec 004)"
  - "não depende de rede; recebe batch já montado"
  - "base_coin vem de quem chama (passar p/ remover sufixo) — ou normalizar no MarketAnalyzer"
```

---

## 6. Verificação (matriz — roda na spec 004)

```yaml
test_cases:
  - id: V1
    in:  '{ "winning_coin":"BTC", "final_confidence":"95", "decision_summary":"ok" }'
    expect: "confidence vira int 95 (sem TypeError)"           # AI-01a
  - id: V2
    in:  '{ "winning_coin":"DOGE", "final_confidence":92 }   # DOGE não no batch'
    expect: "winning_coin => NENHUMA, confidence => 0, auditado"   # AI-01b
  - id: V3
    in:  '{ "winning_coin":"  btcusdt ", "final_confidence":91, "decision_summary":"x" }'
    expect: "normaliza p/ BTC (se BTC no batch)"               # AI-01c
  - id: V4
    in:  '{ "winning_coin":"BTC", "final_confidence":150 }'
    expect: "clamp p/ 100"                                     # AI-01d
  - id: V5
    in:  '{ "winning_coin":"BTC", "final_confidence":90 }   # sem decision_summary'
    expect: "decision_summary = texto padrão (sem IndexError)" # AI-01e
  - id: V6
    in:  '{}'
    expect: "NENHUMA/HOLD + confidence 0"                      # AI-01f
  - id: V7
    in:  'null'
    expect: "ERROR_503 (não-dict)"
  - id: V8
    in:  '{ "winning_coin":"NENHUMA", "final_confidence":99 }'
    expect: "confidence forçado a 0 (consistência veto)"       # step_4
  - id: V9
    in:  'texto não-JSON'
    expect: "ERROR_503 (parse guard preserva comportamento)"   # AI-01g
  - id: V10_regressao
    in:  '{ "winning_coin":"BTC", "final_confidence":96, "decision_summary":"forte reversão" }   # BTC no batch'
    expect: "passa intacto; compra/swap funcionam como hoje"
```

---

## 7. Riscos & mitigação

```yaml
risks:
  - risk: "Normalização agressiva descartar trade válido (ticker levemente diferente)"
    mit:  "remoção de sufixo da base + match case-insensitive cobre os casos reais; logar near-miss p/ ajustar"
  - risk: "Remover sufixo errado em base != USDT (ex.: moeda terminando em letras da base)"
    mit:  "remover só se termina exatamente com base_coin E o prefixo existe no batch; senão tentar match direto"
  - risk: "Esconder degradação real da IA atrás de vetos silenciosos"
    mit:  "auditoria (step_5) torna correções visíveis; métrica de 'vetos por validação' observável"
```

---

## 8. Definição de pronto (DoD)

- [ ] `_normalize_verdict` implementada como função pura e integrada nos dois métodos.
- [ ] Saída de `analyze_batch`/`analyze_swap` **sempre** conforme seção 3.
- [ ] Fail-closed comprovado: nenhuma entrada inválida abre/troca posição (V1–V9).
- [ ] Regressão V10 ok: caminho feliz inalterado.
- [ ] Correções de validação auditadas sem vazar a chave da API.
- [ ] Testes da matriz seção 6 passando (executados na spec 004).
- [ ] Revisado e aprovado pelo Micael.

---

## 9. Pendências para o Micael

1. **Ticker alucinado (AI-01b):** rebaixar para veto silencioso (proposto) ou logar como WARNING destacado por ser sinal de prompt/modelo desalinhado?
2. **Limite de `decision_summary`:** 4000 chars basta, ou você quer relatórios mais longos no painel?
3. **Confiança fracionária:** arredondar para int (proposto) ou preservar float? Os limiares (90/95) funcionam com ambos.
