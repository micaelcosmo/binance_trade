# Configuração Docker

Antes do primeiro `docker compose up`, crie os arquivos montados no container:

```bash
cp config/user.cfg.exemple config/user.cfg
cp config/supported_coin_list.exemple config/supported_coin_list.txt
cp .env.example .env
```

Edite `config/user.cfg` com as chaves Binance e `testnet = False` (ou `True` para testnet). No `.env`, **não defina** `API_KEY`, `API_SECRET_KEY` nem `TESTNET` se usar o `user.cfg` — `TESTNET=false` no ambiente vira string truthy e causa erro `-2015` em conta real.

- `config/user.cfg` — montado em `/app/user.cfg` (somente leitura)
- `config/supported_coin_list.txt` — lista de moedas (uma por linha, sem USDT)

`config/user.cfg` está no `.gitignore` e no `.cursorignore` e não deve ser commitado. O `.env` na raiz também está ignorado pelo Git e pelo Cursor.
