# ADR-0011 · Commits semânticos com versão; só minor/patch (nunca major)

- **Status:** Accepted
- **Data:** 2026-11-10 (formaliza prática já usada desde v3.6.x)
- **Origem:** histórico git + sessão E0–E4

## Contexto
A versão exibida no painel vem de `git describe --tags`. O histórico já usa mensagens no formato `tipo(escopo): descrição vX.Y.Z`. A linha v3 é a linha de produto vigente; um salto de major sinalizaria quebra que não é desejada.

## Decisão
- Mensagem: `tipo(escopo): descrição em pt-BR, minúsculas [vX.Y.Z]` — tipos `feat`, `fix`, `test`, `docs`, `chore`, `refactor`, `perf`.
- Commit que muda comportamento entregável leva a versão no fim da mensagem e tag anotada correspondente.
- **feat → minor** (ex.: v3.6.7 → v3.7.0); **fix/perf/ajuste → patch** (v3.7.0 → v3.7.1). `docs`/`test`/`chore` podem ficar sem bump.
- **Nunca** subir major (v3 → v4), mesmo em mudança grande.
- Só o orquestrador commita/tagueia (ADR-0010).

## Consequências
- Fallback de versão hardcoded em `app.py` (`"v3.6.6"`) fica defasado — preferir sempre a tag.
- "painel.py morre na v3" (ADR-0004) passa a significar "dentro da linha v3", não "na v4".
