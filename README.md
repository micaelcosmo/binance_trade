```markdown
# 📈 Binance Trade Bot Pro

![Version](https://img.shields.io/badge/version-v2.0.0-blue) ![License](https://img.shields.io/badge/license-MIT-green)

Um bot de trading algorítmico automatizado para a corretora Binance, focado em acúmulo inteligente de criptoativos (Jumps), gestão de risco automatizada e realização de lucros via Trailing Stop Loss Global.

Este projeto é um *fork* evoluído da arquitetura clássica de trading, aprimorado com uma interface gráfica interativa (Dashboard), proteção dinâmica contra quedas de mercado e um sistema matemático de lucros compostos.

> 🌟 **Novidades da v2.0.0:** Introdução do Cockpit UI em Tkinter, IPC via JSON local para status em tempo real, e o novo motor de Trailing Stop Loss Global para garantir lucros líquidos em USDT.

---

## 🧠 Como Funciona a Estratégia?

O núcleo deste bot opera sob um paradigma de "Fazendeiro" (Acumulação) combinado com um "Caçador" (Trailing Stop). Ele foi desenhado para eliminar o fator emocional das operações de criptomoedas.

### 1. O Motor de Acúmulo (Jumps)

O bot não faz "Buy and Hold" cego. Ele varre o mercado em tempo real através de conexões WebSocket buscando oportunidades de "pulo" (*Jump*). Se você possui a moeda A, e a moeda B apresenta uma variação de preço favorável que cubra as taxas da corretora e garanta um lucro mínimo real (definido pelo parâmetro `scout_margin`), o bot executa a troca. O objetivo primário é **aumentar a quantidade bruta de moedas** na sua carteira.

### 2. Trailing Stop Loss Global (A Máquina de Lucro)

Diferente de estratégias engessadas que ficam presas em moedas desvalorizadas, este bot monitora o **Patrimônio Total em Dólares (USDT)**. 

- **O Gatilho:** Quando o seu saldo total atinge uma meta percentual pré-configurada (`global_take_profit`), o sistema entra em estado de alerta.
- **O Recuo (Trailing):** O bot passa a perseguir o preço como uma sombra. Se o mercado continuar subindo, ele atualiza o pico máximo de lucro. Se o mercado recuar uma porcentagem específica (`trailing_drop`) a partir desse pico, a "coleira" estica e o bot liquida a posição para USDT. Isso garante o lucro líquido no bolso e reinicia o ciclo com uma banca maior (Juros Compostos).

### 3. O Porteiro do Mercado (Histerese de BTC)

O bot utiliza o Bitcoin (BTC) como termômetro global. Se o BTC apresentar um derretimento brusco (configurável em `btc_crash_limit`), o bot entra instantaneamente em **Modo Sobrevivência**, paralisando compras arriscadas e protegendo o capital em Dólar até que o mercado apresente sinais consistentes de recuperação (`btc_recover_limit`).

### 4. Dashboard Interativo (Cockpit de Operações)

Acompanhe cada cálculo sob o capô através de um painel visual construído nativamente em Python (Tkinter). O painel entrega em tempo real:

- Saldo Base vs. Saldo Atual (P/L Dinâmico).
- Snapshot visual da moeda Anterior vs. Moeda Atual (Prova matemática do acúmulo).
- Monitoramento do gatilho e estado do Trailing Stop Global.
- Radar das Altcoins Aptas (Quentes) e em Cooldown (Geladeira).

---

## 💡 Créditos e Origem

Este projeto iniciou como uma ramificação (fork) inspirado no robusto motor open-source do [binance-trade-bot](https://github.com/edeng23/binance-trade-bot), evoluindo e divergindo para uma arquitetura "Pro" voltada a interfaces gráficas (IPC via JSON local), injeção de lógicas de Stop Móvel em nível de portfólio e otimizações pesadas nas rotinas de requisição.

---

## ⚙️ Instalação e Configuração

### Pré-requisitos

- **Python 3.9+** instalado no sistema.
- Conta na **Binance** com chaves de API geradas (Permissões de `Leitura` e `Trade` habilitadas. Por segurança, **NÃO** habilite permissões de saque).
```

### Passo a Passo de Setup

**1. Clone o repositório para a sua máquina:**

```bash
git clone [https://github.com/micaelcosmo/binance_trade.git](https://github.com/micaelcosmo/binance_trade.git)
cd binance_trade
```

**2. Crie e ative um Ambiente Virtual (VENV):**
Isso garante que as bibliotecas do bot não entrem em conflito com o seu sistema.
```bash
# No Windows
python -m venv venv
venv\Scripts\activate

# No Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

**3. Instale as dependências do projeto:**
```bash
pip install -r requirements.txt
```

**4. Arquivos de Configuração:**
- Faça uma cópia do arquivo de manifesto para criar a sua configuração local:
  ```bash
  # Windows
  copy user.cfg.example user.cfg
  
  # Linux/Mac
  cp user.cfg.example user.cfg
  ```
- Abra o novo arquivo `user.cfg` em qualquer editor de código. Ele possui um manual completo e comentado em cada linha para você definir o seu nível de risco (margens de Jump, timeouts, gatilhos de Trailing).
- Configure as suas Chaves de API da Binance conforme a estrutura do arquivo base do ambiente (`app.json` ou `.env`).

---

## 🚀 Como Executar

Com o ambiente virtual ativado e as chaves devidamente inseridas, inicie o Cockpit (Dashboard):

```bash
python painel.py
```

A interface gráfica será renderizada. Clique no botão **RUN > Iniciar Bot** no topo da tela para disparar os processos paralelos em segundo plano. Relaxe e acompanhe a mágica acontecer pelo terminal de logs da UI.

---
> ⚠️ **Aviso Legal:** Este software é fornecido "como está", sem garantias de lucro. Criptomoedas são ativos de altíssima volatilidade. Faça testes com valores baixos (ou na Testnet), opere com responsabilidade e gerencie o seu próprio risco financeiro.
```