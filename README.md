Markdown
# 📈 Binance Trade Bot Pro - AI Edition

<img src="https://img.shields.io/badge/version-v3.3.0-blue" alt="Version"> <img src="https://img.shields.io/badge/license-MIT-green" alt="License"> <img src="https://img.shields.io/badge/python-3.9+-yellow" alt="Python">

Um terminal de trading algorítmico automatizado para a corretora Binance. O projeto utiliza uma arquitetura quantitativa avançada focada em Swing Trade, unindo **Matemática de Indicadores (Pandas-TA)** e um **Comitê de Inteligência Artificial Institucional (Google Gemini)** para gestão de risco, análise de lote e maximização de lucros.

---

## ✨ Principais Funcionalidades

* 🧠 **Gestor Institucional IA (Três Olhos):** O bot não gasta tokens analisando ruídos. Ele compila um *Dossiê Quantitativo* tridimensional (Macro 4H, Elástico 1H, Gatilho 15m com MACD) e envia em lote para o **Gemini 2.5 Flash-Lite**. A IA escolhe a melhor assimetria matemática.
* 🛡️ **Filtros Dinâmicos de Proteção (ATR):** Fim dos "achismos" de porcentagem. O bot calcula o True Bottom exigindo que a moeda caia mais que 2x o seu próprio ATR (Average True Range).
* 🎯 **Trailing Stop Dinâmico & R:R Fixo:** O bot arma um gatilho invisível buscando +1.50% de alvo, protegido por um Stop Loss rígido de no máximo -3.50%. Ele persegue o preço para cima e corta as perdas rápido.
* 🚨 **Manual Override (Panic Button):** Assuma o controle. Um botão de Venda Forçada na interface permite que o usuário feche a operação a mercado instantaneamente, registrando o P/L no histórico de forma transparente.
* 👑 **Regra de Ouro (Auto-Switch):** Se o bot ficar preso em uma moeda, o Tribunal de Swap da IA avalia se vale a pena assumir um pequeno prejuízo para migrar para um setup com 95%+ de confiança.
* 💻 **Dashboard Interativo (UI):** Interface nativa (Tkinter) com P/L real, gráficos de velas, placar de Win/Loss, histórico diário e o parecer auditado ao vivo do comitê de Inteligência Artificial.

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
O bot utiliza pandas para cálculos técnicos, o SDK nativo google-genai para a IA e exige uma versão específica do Websockets para a conexão com a Binance.
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
* **GOOGLE_API_KEY:** Gere uma chave gratuita no [Google AI Studio](https://aistudio.google.com/) para habilitar o Oráculo de IA. Sem ela, o bot rodará em modo "cego" (Bypass).

**B. Lista de Ativos (`supported_coin_list.txt`)**
```bash
cp supported_coin_list.example supported_coin_list.txt
```
Abra o `supported_coin_list.txt` e liste os tokens que o bot deve incluir no Dossiê Quantitativo para a IA analisar. Adicione apenas o nome da moeda (uma por linha), sem o par da base (USDT). Exemplo: `BTC`, `CFG`, `SOL`.

---

## 🚀 Como Executar

Com o ambiente ativado e os arquivos configurados, inicie a interface gráfica do painel:
```bash
python painel.py
```
O Dashboard abrirá. Selecione sua estratégia e clique no botão **"RUN > Iniciar Bot"**. Acompanhe a varredura do mercado, a auditoria de tokens da API e os diagnósticos da IA diretamente na tela.

---

## ❓ FAQ & Solução de Problemas (Troubleshooting)
Se o bot não iniciar ou apresentar erros no console, confira as soluções para os problemas mais comuns:

### ⏱️ Erro de Timestamp (APIError code=-1021)
* **O erro:** `APIError(code=-1021): Timestamp for this request is outside of the recvWindow.`
* **O motivo:** O relógio do seu computador está dessincronizado com os servidores da Binance em mais de 5 segundos.
* **A solução:**
  * **No Windows:** Clique com o botão direito no relógio da barra de tarefas > "Ajustar data/hora" > Clique no botão **"Sincronizar agora"**.

### 🕸️ Conflito de Dependência (Websockets)
* **O erro:** `unicorn-binance-websocket-api requires websockets==11.0.3, but you have websockets 16.0...`
* **O motivo:** O motor da Binance exige uma versão antiga da biblioteca de rede, enquanto pacotes mais novos podem ter forçado uma atualização.
* **A solução:** Force o downgrade seguro da biblioteca com o comando:
```bash
pip install websockets==11.0.3
```

---

## ⚠️ Disclaimer (Aviso Legal)
Este software é um projeto de código aberto com fins educacionais e experimentais. Não é um conselho financeiro. O mercado de criptomoedas é altamente volátil. Os desenvolvedores não se responsabilizam por perdas financeiras. Utilize por sua conta e risco, e teste exaustivamente com quantias pequenas antes de alocar capital significativo.