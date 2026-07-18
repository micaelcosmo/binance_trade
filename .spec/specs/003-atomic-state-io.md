# 003 · Escrita Atômica de Estado (JSON e Flags)

> **Status:** Implementado · **Prioridade:** P1 · **Fase:** A (Blindagem)
> **Issue coberta:** `DATA-02` (race de I/O — leitura de JSON parcial)
> **Relaciona:** contrato `state-and-flags.md`

---

## 1. Problema

Motor e UI trocam estado por arquivos, **sem lock**. A escrita atual é:

```python
with open("bot_status.json", "w", ...) as f:
    json.dump(payload, f)   # janela em que o arquivo está pela metade
```

Se a UI (`monitor_bot_status`, poll ~1s) ler exatamente durante a escrita, pega JSON truncado → `json.load` lança → hoje é engolido por `try/except`, mas o painel perde aquele frame de estado. Em flags/estado persistido, o risco é corrupção.

---

## 2. Solução

Escrita **atômica** via arquivo temporário no mesmo diretório + `os.replace` (rename atômico no mesmo volume, POSIX e Windows):

```yaml
pattern:
  - "escreve conteúdo completo em .tmp no MESMO diretório do destino"
  - "flush + fsync"
  - "os.replace(tmp, destino)  # troca atômica: leitor vê versão antiga OU nova completa"
  - "em erro: remove o tmp e propaga"
garantia: "nenhum leitor jamais observa um arquivo parcialmente escrito"
```

Módulo novo, **sem dependências**: [binance_trade_bot/atomic_io.py](../../binance_trade_bot/atomic_io.py)

```yaml
api:
  atomic_write_text(path, text, encoding='utf-8'): "escrita atômica de texto"
  atomic_write_json(path, data, encoding='utf-8', **json_kwargs): "dumps + atomic_write_text"
```

---

## 3. Pontos de aplicação

```yaml
substituicoes:
  profit_gain_strategy.py:
    - "_write_json_ui  -> atomic_write_json(bot_status.json, ..., ensure_ascii=False, indent=2)"
    - "_save_state     -> atomic_write_json(profit_gain_state.json, ...)"
  app.py:
    - "_save_gui_state           -> atomic_write_json(gui_state.json, ...)"
    - "handle_reset_scoreboard   -> atomic_write_json nos rewrites de status/pg_state"
    - "flags (start bot status reset, etc.) -> atomic_write_text/json"
  flags_UI:
    - "cooldown/bb_std/add_trade/force_sell/update/reset -> atomic_write_text"
observacao: "flags são one-shot e pequenas; atomicidade evita o motor ler flag meio-escrita"
```

Leitura permanece com `try/except` (defesa em profundidade); com `os.replace` o caso de parcial deixa de existir.

---

## 4. Verificação (spec 004)

```yaml
tests:
  - "atomic_write_json cria arquivo com conteúdo íntegro e parseável"
  - "sobrescrita mantém arquivo sempre válido (nunca vazio/parcial)"
  - "não deixa arquivos .tmp órfãos no diretório após sucesso"
  - "erro no meio não corrompe o destino pré-existente"
  - "regressão: schema de bot_status.json inalterado (contrato)"
```

---

## 5. Riscos

```yaml
risks:
  - risk: "tmp em diretório diferente do destino => os.replace cross-device falha"
    mit:  "tmp criado SEMPRE no dirname(destino)"
  - risk: "fsync custoso a cada 1s"
    mit:  "arquivos pequenos; custo desprezível; correção > microperf"
  - risk: "*.tmp aparecendo no git"
    mit:  "prefixo '.tmp_' + já removidos por os.replace; *.json/*.flag já ignorados"
```
