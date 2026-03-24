# 📈 Binance Trade Bot Pro - AI Edition

<img src="https://img.shields.io/badge/version-v2.7.7-blue" alt="Version"> <img src="https://img.shields.io/badge/license-MIT-green" alt="License"> <img src="https://img.shields.io/badge/python-3.9+-yellow" alt="Python">

Um terminal de trading algorítmico automatizado para a corretora Binance. Originalmente focado em acúmulo de criptomoedas, o projeto evoluiu para uma arquitetura quantitativa completa, unindo **Análise Técnica Clássica** e **Inteligência Artificial (Google Gemini)** para gestão de risco avançada e maximização de lucros.

---

## ✨ Principais Funcionalidades

* 🧠 **Oráculo IA (Google Gemini 2.5):** O bot não compra no escuro. Após os filtros matemáticos, os últimos candles são enviados para a IA analisar Price Action, volume e contexto, barrando compras em topos falsos ou exaustão de mercado.
* 📊 **Filtros Matemáticos (TA):** Varredura de mercado utilizando cruzamento de Médias Móveis Exponenciais (EMA 9x21) e Índice de Força Relativa (RSI < 70) para identificar tendências de alta seguras.
* 🎯 **Trailing Stop Dinâmico:** Esqueça o "Take Profit" fixo. O bot identifica quando uma operação está lucrando, arma um gatilho invisível e persegue o preço para cima. Ele só vende quando a moeda perde a força, espremendo o máximo de lucro possível de cada pernada de alta.
* 🛡️ **Regra de Ouro (Auto-Switch):** Se o mercado virar e o bot ficar "preso" em uma moeda lateralizada ou em queda lenta por muito tempo, ele escaneia o mercado no background, encontra uma oportunidade melhor e migra o saldo automaticamente.
* 💻 **Dashboard Interativo (UI):** Interface gráfica nativa (Tkinter) para visualização em tempo real de P/L, minigráficos de velas (5m), placar de Win/Loss, moedas na "Geladeira" e o veredito ao vivo da IA.

---

## ⚙️ Pré-requisitos e Instalação

### 1. Clonando o repositório
```bash
git clone https://github.com/micaelcosmo/binance_trade.git
cd binance_trade
```

### 2. Ambiente Virtual (Recomendado)
Isole as dependências do projeto para evitar conflitos com o seu sistema operacional:
```bash
python -m venv venv
# No Windows:
venv\Scripts\activate
# No Linux/Mac:
source venv/bin/activate
```

### 3. Instalando Dependências
O bot utiliza `pandas` para cálculos técnicos, `langchain` para a IA e exige uma versão específica do ORM do banco de dados para retrocompatibilidade.
```bash
pip install -r requirements.txt
```

### 4. Configuração do Bot (`.cfg` e `.txt`)
O bot precisa de dois arquivos de configuração para rodar. Você deve criar cópias dos templates disponibilizados no repositório:

**A. Credenciais e Configurações Globais (`user.cfg`)**
```bash
cp user.cfg.example user.cfg
```
Abra o `user.cfg` recém-criado e configure:
* **Binance API Keys:** Suas chaves de leitura e trade (⚠️ *Recomendação de segurança: Desative a permissão de saque na Binance*).
* **GOOGLE_API_KEY:** Gere uma chave gratuita no [Google AI Studio](https://aistudio.google.com/) para habilitar o Oráculo de IA. Sem ela, o bot rodará em modo "cego" (apenas matemática).

**B. Lista de Ativos (`supported_coin_list.txt`)**
```bash
cp supported_coin_list.example supported_coin_list.txt
```
Abra o `supported_coin_list.txt` e liste os tokens que o bot deve monitorar. Adicione apenas o nome da moeda (uma por linha), sem o par da base (USDT). Exemplo: `BTC`, `CFG`, `SOL`.

---

## 🚀 Como Executar

Com o ambiente ativado e os arquivos configurados, inicie a interface gráfica do painel:
```bash
python painel.py
```
O Dashboard abrirá. Selecione sua estratégia e clique no botão **"RUN > Iniciar Bot"**. Acompanhe a varredura do mercado, o status do trailing stop e os diagnósticos da IA diretamente na tela.

---

## ❓ FAQ & Solução de Problemas (Troubleshooting)

Se o bot não iniciar ou apresentar erros no console, confira as soluções para os problemas mais comuns relatados pela comunidade:

### ⏱️ Erro de Timestamp (APIError code=-1021)
* **O erro:** `APIError(code=-1021): Timestamp for this request is outside of the recvWindow.`
* **O motivo:** O relógio do seu computador está dessincronizado com os servidores da Binance em mais de 5 segundos. É uma trava de segurança da corretora contra *replay attacks*.
* **A solução:**
  * **No Windows:** Clique com o botão direito no relógio da barra de tarefas > "Ajustar data/hora" > Clique no botão **"Sincronizar agora"**.
  * **No Linux/Mac:** Force a sincronização do NTP (Network Time Protocol) através do terminal.

### 🗄️ Erro de Banco de Dados / ORM (SQLAlchemy ArgumentError)
* **O erro:** `sqlalchemy.exc.ArgumentError: Column expression, FROM clause, or other columns clause element expected...`
* **O motivo:** A versão do SQLAlchemy no seu ambiente atualizou acidentalmente para a `v2.0+`, quebrando a compatibilidade de sintaxe (`select([])`) utilizada pelo motor interno do bot.
* **A solução:** Faça o downgrade da biblioteca para a versão estável da ramificação 1.4 rodando os comandos abaixo com a venv ativada:
  ```bash
  pip uninstall SQLAlchemy -y
  pip install SQLAlchemy==1.4.52
  ```

---

## ⚠️ Disclaimer (Aviso Legal)
Este software é um projeto de código aberto com fins educacionais e experimentais. **Não é um conselho financeiro.** O mercado de criptomoedas é altamente volátil. Os desenvolvedores não se responsabilizam por perdas financeiras. Utilize por sua conta e risco, e teste exaustivamente com quantias pequenas antes de alocar capital significativo.