# ADR-0010 · Fluxo de trabalho multi-agente com orquestrador único + STATUS/TEMPO via `track.py`

- **Status:** Accepted
- **Data:** 2026-11-10
- **Origem:** sessão de desenvolvimento E0–E4 (épico E0)

## Contexto
O desenvolvimento passou a ser feito por vários agentes de IA em paralelo (spec, simulação, UI). Sem coordenação, há conflito de escrita, perda de contexto e o Micael não enxerga o que cada agente faz nem quanto tempo leva.

## Decisão
- **Um único orquestrador** distribui tasks, integra resultados e é o **único que faz git add/commit/push/tag**. Agentes trabalham em escopo de pastas explícito e não editam fora dele.
- Rastreamento obrigatório via CLI `devpanel/track.py`:
  - `agent` (registro + heartbeat a cada mudança de step, no máximo ~10 min de intervalo),
  - `task` (status `todo|doing|blocked|review|done|cancelled`, steps com `--add-step/--step-doing/--step-done`),
  - `epic`, `event`, `decision` (perguntas ao Micael; `--blocking` só quando impede seguir — senão segue com a recomendação).
- `.spec/STATUS.md` e `.spec/TEMPO.md` são **gerados** (markdown + bloco YAML fonte de verdade); nunca editados à mão. Escrita com lock `.spec/.track.lock` (expira em 30 s) + escrita atômica.
- Painel `devpanel/server.py` (http://127.0.0.1:5055) lê esses arquivos, alerta agente `active` sem heartbeat > 15 min e permite ao Micael responder decisões.

## Consequências
- Visibilidade em tempo real do trabalho e dos tempos (TEMPO.md).
- Decisões do dono ficam registradas com pergunta/opções/recomendação/resposta.
- Agentes dependem do CLI funcionando; `.spec/.track.lock` é gitignored.
