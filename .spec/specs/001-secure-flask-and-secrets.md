# 001 · Blindagem do Painel Web (Flask) e Gestão de Segredos

> **Status:** Draft · **Prioridade:** P0 (CRÍTICO) · **Fase:** A (Blindagem)
> **Depende de:** — · **Bloqueia:** qualquer exposição remota do painel
> **Issues cobertas:** `SEC-01` (Flask inseguro), `SEC-02` (segredos)
> **Decisão-base:** acesso remoto ao painel está **planejado** → segurança vira pré-requisito, não opcional.
> **Decisão-base (auth):** modelo **JWT com mentalidade AAA** (Authentication, Authorization, Accounting), **configurável via `user.cfg`**.
> **Regra inviolável:** esta spec **não lê nem ecoa** `user.cfg`/`.env`. Quem lê `user.cfg` é o `config.py` em runtime; o agente só documenta chaves no `user.cfg.exemple` e estende o parser.

---

## 1. Contexto e motivação

O painel `app.py` (Flask + SocketIO) hoje roda como ambiente de **desenvolvimento** exposto em `0.0.0.0`. Ele controla um bot que opera **capital real**: pode forçar vendas, zerar placar, ajustar risco e disparar `git pull`. Expor isso remotamente no estado atual é entregar o cofre com a porta aberta.

### Estado atual (evidências no código)

```yaml
# app.py
findings:
  - id: SEC-01a
    where: "app.py:18"
    issue: "SECRET_KEY hardcoded ('binance_bot_pro_dev_key_secure')"
    impact: "sessões/cookies forjáveis; segredo público no repo"
  - id: SEC-01b
    where: "app.py:519"
    issue: "socketio.run(app, debug=True, host='0.0.0.0', port=5000)"
    impact: "debug=True → Werkzeug debugger = RCE remota; 0.0.0.0 = escuta em todas interfaces"
  - id: SEC-01c
    where: "app.py (todos os @socketio.on)"
    issue: "nenhum evento exige autenticação"
    impact: "qualquer um na rede dispara start/stop/force_sell/update"
  - id: SEC-01d
    where: "app.py:19"
    issue: "cors_allowed_origins='*'"
    impact: "qualquer origem abre socket; CSRF/websocket hijacking"
  - id: SEC-01e
    where: "transporte"
    issue: "sem TLS/HTTPS"
    impact: "credenciais de sessão e comandos trafegam em claro"

# .gitignore (auditoria SEC-02)
gitignore_status:
  cobre: [user.cfg, "*.json", "*.flag", "*.log", crypto_trading.db]
  GAP_critico:
    - ".env NÃO está no .gitignore"   # risco de commit acidental de segredos
  observacao:
    - "*.json ignora tudo (inclui gui_state/profit_gain_state) — ok p/ segredo, mas app.json é rastreado por já ter sido commitado"
```

---

## 2. Objetivo

Tornar o painel **seguro para exposição remota** sem alterar **nenhuma** lógica de trading. Ao final:

- Nenhum segredo no código-fonte.
- Sem debugger remoto.
- Toda ação sensível exige sessão autenticada.
- Tráfego cifrado (TLS) e origens restritas.
- `.env` impossível de commitar por acidente.

### Não-objetivos (fora desta spec)

- Refactor do motor (`ARCH-01`) → spec 005.
- Validação da saída da IA (`AI-01`) → spec 002.
- Escrita atômica de estado (`DATA-02`) → spec 003.
- Multi-usuário/RBAC, painel admin avançado. Aqui: **single-user** basta.

---

## 3. Requisitos

```yaml
requirements:
  R1_secret:
    must: "Flask SECRET_KEY e JWT signing secret carregados de config (user.cfg) ou env; sem fallback hardcoded em prod"
    accept: "iniciar em prod sem secret definido → falha explícita (não usa default)"
  R2_no_debug:
    must: "debug controlado por env (APP_ENV); prod => debug=False, sem reloader"
    accept: "em prod, acessar rota inexistente NÃO mostra Werkzeug traceback/console"
  R3_auth:
    must: "Authentication via JWT; login emite token; todo @socketio.on sensível rejeita token ausente/inválido/expirado"
    accept: "socket sem JWT válido recebe erro e NÃO executa start/stop/force_sell/update"
  R3b_authz:
    must: "Authorization por escopos/role no claim do JWT; eventos sensíveis exigem escopo correspondente"
    accept: "token autenticado mas sem o escopo exigido => ação negada (403)"
  R3c_acct:
    must: "Accounting: trilha de auditoria append-only de toda ação sensível (quem/o quê/quando/resultado)"
    accept: "force_sell/start/stop/update geram registro de auditoria com principal e timestamp"
  R3d_config:
    must: "parâmetros de auth (usuário, hash, segredo, expiração, escopos) configuráveis via user.cfg; override por env"
    accept: "alterar credencial no user.cfg muda o login sem editar código"
  R4_cors:
    must: "cors_allowed_origins restrito a allowlist via env (não '*') em prod"
    accept: "origem fora da allowlist não estabelece socket em prod"
  R5_tls:
    must: "TLS terminado (proxy reverso recomendado) + cookies Secure/HttpOnly/SameSite"
    accept: "http→https redirect; cookie de sessão com flags de segurança"
  R6_bind:
    should: "bind configurável; default seguro (127.0.0.1) salvo override explícito"
    accept: "sem APP_HOST definido, não escuta em 0.0.0.0"
  R7_env_hygiene:
    must: "adicionar .env ao .gitignore; documentar variáveis em .env.exemple"
    accept: "git check-ignore .env => ignorado; .env.exemple sem valores reais"
  R8_no_regression:
    must: "lógica de trading e contrato bot_status.json/flags inalterados"
    accept: "fluxo start→scan→trade idêntico ao atual com sessão autenticada"
```

---

## 4. Design proposto

Princípio: **mínima cirurgia no `app.py`**, segurança como camadas em volta. Trading intocado.

### 4.1 Configuração — fonte de verdade `user.cfg` (+ override por env)

Auth é **configurável via `user.cfg`**. O `config.py` (que já faz parse anti-crash) ganha uma nova seção
e expõe os valores ao `app.py`. Precedência: **env var > user.cfg > default seguro**. Documentar tudo no
`user.cfg.exemple`. O agente **não** lê o `user.cfg` real — só edita o `.exemple` e o parser.

```yaml
# Nova seção em user.cfg (exemplo de chaves — valores reais NUNCA versionados)
cfg_section: "[panel_auth]"
keys:
  enabled:            "true|false  (default: true em prod)"
  jwt_secret:         "segredo HMAC para assinar o JWT (obrigatório em prod; mín. 32 bytes)"
  jwt_algorithm:      "HS256 (default)"
  jwt_access_ttl_min: "expiração do access token em minutos (default: 30)"
  jwt_refresh_ttl_min:"expiração do refresh token (default: 1440 = 24h; 0 = sem refresh)"
  jwt_issuer:         "binance-bot-panel (default) — claim 'iss'"
  panel_user:         "usuário do painel"
  panel_password_hash:"hash da senha (werkzeug/pbkdf2 ou bcrypt) — NUNCA a senha pura"
  panel_scopes:       "CSV de escopos do usuário (ver 4.2). Ex.: trade:control,trade:sell,system:update,read"
  login_max_attempts: "tentativas antes de lockout (default: 5)"
  login_lockout_min:  "duração do lockout (default: 15)"

env_overrides:   # sobrepõem user.cfg quando presentes (deploy/cloud)
  APP_ENV:             "dev | prod (default: dev) — controla debug/host/cors estritos"
  PANEL_JWT_SECRET:    "override de jwt_secret"
  PANEL_PASSWORD_HASH: "override de panel_password_hash"
  APP_HOST:            "bind (default: 127.0.0.1)"
  APP_PORT:            "porta (default: 5000)"
  APP_ALLOWED_ORIGINS: "CSV de origens permitidas no socket (prod)"

config_py_impact:
  - "novo bloco get_safe_* para [panel_auth] com mesma filosofia anti-crash"
  - "Config expõe: AUTH_ENABLED, JWT_SECRET, JWT_ALG, JWT_ACCESS_TTL, JWT_REFRESH_TTL, JWT_ISSUER, PANEL_USER, PANEL_PASSWORD_HASH, PANEL_SCOPES, LOGIN_MAX_ATTEMPTS, LOGIN_LOCKOUT_MIN"
  - "em prod, jwt_secret/panel_password_hash ausentes => erro explícito no boot"
new_dependency: "PyJWT (adicionar ao requirements.txt)"
```

### 4.2 AAA — Authentication, Authorization, Accounting (JWT)

```yaml
# --- A1: AUTHENTICATION (provar identidade → emitir JWT) ---
authentication:
  login:
    - "POST /api/login {user, password}"
    - "valida PANEL_USER + check_password_hash(PANEL_PASSWORD_HASH)"
    - "rate-limit/lockout: login_max_attempts + login_lockout_min (anti brute force)"
    - "sucesso => emite access JWT (e refresh JWT, se ttl>0)"
  token_claims:
    sub:    "PANEL_USER"
    iss:    "jwt_issuer"
    iat/exp:"emitido/expira (jwt_access_ttl_min)"
    scopes: "lista derivada de panel_scopes"
    typ:    "access | refresh"
  refresh:
    - "POST /api/refresh com refresh token válido => novo access token"
    - "se jwt_refresh_ttl_min=0, sem refresh (re-login ao expirar)"
  transport:
    - "cliente guarda token; envia em Authorization: Bearer <jwt> (HTTP) e no auth payload do socket"
    - "verificação: assinatura (jwt_secret/jwt_algorithm) + exp + iss"

# --- A2: AUTHORIZATION (o que a identidade pode fazer) ---
authorization:
  model: "escopos no claim 'scopes' do JWT (RBAC leve, single-user hoje, extensível)"
  scopes:
    read:           "ver painel/estado (default mínimo)"
    trade:control:  "start/stop do bot, ajustes de cooldown/bb_std, add_trade"
    trade:sell:     "venda forçada (force_sell) — escopo separado por ser destrutivo"
    system:update:  "disparar git pull/auto-update"
  enforcement:
    - "decorator @require_scope('...') nas rotas HTTP sensíveis"
    - "guard nos @socketio.on: valida JWT + escopo exigido por evento"
  event_scope_map:
    connect:               read
    request_dossier:       read
    request_ai_report:     read
    request_daily_history: read
    start_bot:             trade:control
    stop_bot:              trade:control
    cycle_cooldown:        trade:control
    cycle_bb_std:          trade:control
    add_trade_chance:      trade:control
    reset_initial_balance: trade:control
    reset_scoreboard:      trade:control
    force_sell_action:     trade:sell
    request_update:        system:update

# --- A3: ACCOUNTING (trilha de auditoria — opera capital real) ---
accounting:
  what: "registrar toda ação sensível: principal(sub), evento, escopo, timestamp, IP origem, resultado(ok/negado/erro)"
  where: "arquivo append-only logs/audit.log (NDJSON) — fora de *.json do gitignore? ver nota"
  format_example: '{"ts":"...","sub":"micael","event":"force_sell_action","scope":"trade:sell","ip":"...","result":"ok"}'
  rules:
    - "nunca logar o JWT, a senha, o hash, nem chaves Binance/Google"
    - "log de negação (403/expirado) também é auditado (detecção de abuso)"
    - "rotação de log para não crescer infinito"
  gitignore_note: "logs/*.log já é ignorado; manter audit.log sob logs/ garante que não vaze"
```

### 4.3 Fluxo resumido

```text
[/api/login] --creds--> valida (user.cfg) --ok--> emite JWT(scopes,exp)
   front guarda token
[socket connect]  --Bearer JWT--> verifica assinatura+exp+iss --ok--> sessão socket marcada
[evento sensível] --> checa escopo do evento vs scopes do JWT
        ├─ ok        -> executa + AUDITA (result: ok)
        └─ sem escopo -> recusa 403 + AUDITA (result: negado)
[token expira] --> evento recusado -> front usa /api/refresh ou redireciona a /login
```

### 4.4 Bootstrap seguro (substitui o bloco `__main__` de `app.py`)

```yaml
boot_logic:
  - "carregar dotenv + Config() (lê user.cfg via config.py)"
  - "resolver auth params: env override > user.cfg > default"
  - "APP_ENV=prod => exigir JWT_SECRET e PANEL_PASSWORD_HASH; abortar com msg clara se faltar"
  - "app.secret_key = secret resolvido (sem default hardcoded em prod)"
  - "instanciar verificador JWT (PyJWT) com JWT_SECRET/JWT_ALG/JWT_ISSUER"
  - "debug = (APP_ENV == 'dev')"
  - "host = APP_HOST or '127.0.0.1'   # nunca 0.0.0.0 implícito"
  - "cors = '*' só em dev; em prod = APP_ALLOWED_ORIGINS"
  - "se AUTH_ENABLED=false (apenas dev/localhost): logar WARNING bem visível"
  - "socketio.run(app, host, port, debug)"
```

### 4.5 TLS / exposição remota (operacional, fora do código)

```yaml
tls_strategy:
  recomendado: "proxy reverso (Caddy/Nginx) termina TLS → app em 127.0.0.1:5000"
  alternativa: "túnel (Cloudflare Tunnel) — não abre porta no host"
  evitar: "expor Flask dev server direto na internet"
  pendente_micael: "onde hospedar (VPS própria vs túnel) — decide a config de TLS"
```

---

## 5. Plano de implementação (incremental, sem quebrar trading)

```yaml
steps:
  - n: 1
    title: "Higiene de segredos"
    actions:
      - "adicionar '.env' ao .gitignore"
      - "criar .env.exemple documentando as env_vars (sem valores reais)"
      - "git log --all -p -- não será rodado aqui; auditar histórico em passo separado se necessário"
    risk: nenhum
  - n: 2
    title: "Config de auth via user.cfg + env"
    actions:
      - "estender config.py: seção [panel_auth] com parse anti-crash"
      - "documentar chaves no user.cfg.exemple (sem valores reais)"
      - "remover SECRET_KEY hardcoded; default só em dev"
      - "debug/host/cors derivados de APP_ENV"
      - "adicionar PyJWT ao requirements.txt"
    risk: baixo
  - n: 3
    title: "AAA — Authentication (JWT)"
    actions:
      - "POST /api/login => valida creds (config) e emite JWT (access+refresh)"
      - "POST /api/refresh; verificador JWT central (assinatura/exp/iss)"
      - "guard no handler 'connect': exige Bearer JWT válido"
      - "lockout/rate-limit no login"
    risk: medio   # mexe no fluxo de conexão da UI
  - n: 3b
    title: "AAA — Authorization (escopos)"
    actions:
      - "@require_scope nas rotas HTTP sensíveis"
      - "event_scope_map aplicado nos @socketio.on (ver 4.2)"
    risk: medio
  - n: 3c
    title: "AAA — Accounting (auditoria)"
    actions:
      - "logger de auditoria append-only (logs/audit.log NDJSON)"
      - "registrar ok/negado/erro de toda ação sensível, sem vazar segredos"
    risk: baixo
  - n: 4
    title: "CORS + cookies + bind seguro"
    actions:
      - "cors_allowed_origins por env em prod"
      - "flags de cookie seguras"
    risk: baixo
  - n: 5
    title: "TLS (operacional)"
    actions:
      - "documentar setup de proxy reverso/túnel em .spec/ ou README ops"
    risk: nenhum (fora do app)
```

---

## 6. Verificação (manual, quando autorizado a executar)

```yaml
test_matrix:
  - id: T1
    check: "prod sem APP_SECRET_KEY => processo aborta com mensagem clara"
  - id: T2
    check: "prod: rota inexistente NÃO expõe debugger Werkzeug"
  - id: T3
    check: "socket sem JWT válido => connect recusado; force_sell não executa"
  - id: T3b
    check: "JWT expirado => evento recusado; /api/refresh emite novo access token"
  - id: T3c_authz
    check: "JWT com escopo 'read' mas sem 'trade:sell' => force_sell negado (403) e auditado"
  - id: T3d_acct
    check: "force_sell/start/update geram linha em logs/audit.log (sem segredos)"
  - id: T3e_config
    check: "trocar panel_password_hash no user.cfg muda o login sem editar código"
  - id: T4
    check: "login válido (escopos completos) => fluxo start/stop/dossiê idêntico ao atual"
  - id: T5
    check: "git check-ignore .env => ignorado"
  - id: T6
    check: "origem fora da allowlist => socket recusado em prod"
  - id: T7
    check: "cookie de sessão tem HttpOnly + Secure (prod) + SameSite"
  - id: T8_regressao
    check: "bot_status.json e arquivos-flag mantêm o mesmo schema/comportamento"
```

> Nada disto roda agora — execução só após aprovação do Micael.

---

## 7. Riscos & mitigação

```yaml
risks:
  - risk: "Auth quebrar a reconexão automática do SocketIO no front (index.html)"
    mit: "tratar evento de recusa no cliente → redirecionar para /login; testar F5/reconnect"
  - risk: "Operador esquecer de setar PANEL_PASSWORD_HASH e travar o próprio acesso"
    mit: "mensagem de erro explícita no boot + script utilitário para gerar hash"
  - risk: "Falsa sensação de segurança sem TLS"
    mit: "documentar que auth sem TLS ainda trafega cookie em claro; TLS é obrigatório p/ remoto"
  - risk: "Segredo já vazado em commit histórico"
    mit: "fora do escopo desta spec; abrir tarefa de rotação de chaves se confirmado"
```

---

## 8. Definição de pronto (DoD)

- [ ] R1, R2, R3, R3b, R3c, R3d, R4–R8 atendidos e verificados (matriz seção 6).
- [ ] AAA completo: JWT emitido/verificado, escopos aplicados, auditoria gravando.
- [ ] Chaves de auth documentadas em `user.cfg.exemple`; `config.py` parseia `[panel_auth]`.
- [ ] `.env` no `.gitignore` + `.env.exemple` documentado; PyJWT no `requirements.txt`.
- [ ] Nenhum segredo no código-fonte (nem JWT secret, nem hash).
- [ ] Lógica de trading e contratos (`bot_status.json`, flags) **inalterados**.
- [ ] Documento de setup de TLS/exposição registrado.
- [ ] Revisado e aprovado pelo Micael.

---

## 9. Pendências para o Micael

1. ✅ **Modelo de auth:** decidido — **JWT (AAA) configurável via `user.cfg`**. (Refletido nas seções 4.1/4.2.)
2. **Refresh token:** manter access(30min)+refresh(24h) como proposto, ou access curto sem refresh (re-login)?
3. **Escopos:** o `event_scope_map` (4.2) separa `trade:sell` de `trade:control` — concorda com essa granularidade, ou prefere um único escopo `admin`?
4. **Hospedagem remota:** VPS própria com proxy reverso (Caddy/Nginx) **ou** túnel (Cloudflare/ngrok)? Define a estratégia de TLS.
5. **Auditoria de histórico:** quer que eu abra uma tarefa para verificar se algum segredo já foi commitado no passado (e rotacionar chaves)?

> Nota de design: colocar `jwt_secret`/`panel_password_hash` no `user.cfg` é coerente — o arquivo já é gitignored e já guarda chaves Binance/Google. O hash da senha (não a senha) e o segredo HMAC ficam fora do código. Env vars permanecem como override para deploy cloud.
