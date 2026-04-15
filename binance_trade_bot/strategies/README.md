# Estratégias (Strategies)

Você que vai desenvolver ou personalizar o bot, pode adicionar sua própria estratégia quantitativa a este diretório. O nome do arquivo deve obrigatoriamente terminar com `_strategy.py` e conter a seguinte estrutura base:

```python
from binance_trade_bot.auto_trader import AutoTrader

class Strategy(AutoTrader):

    def scout(self):
        # Sua lógica customizada de varredura e decisão de mercado aqui
        pass
```

Em seguida, defina a configuração strategy no seu arquivo user.cfg com o nome da sua estratégia. Se você nomeou seu arquivo como custom_strategy.py, você precisará colocar strategy=custom no seu arquivo de configuração.

Você pode organizar suas estratégias em subdiretórios e o bot ainda as encontrará automaticamente.

Abaixo estão as estratégias pré-configuradas no ecossistema:

### 🚀 profit_gain (Principal / Institucional)
A jóia da coroa deste sistema. Uma engine quantitativa de altíssimo nível aliada à Inteligência Artificial (LLM), focada em buscar operações precisas de Reversão à Média com gerenciamento de risco agressivo.

O Porteiro Python: Filtra o mercado matematicamente em tempo real, exigindo quedas agudas (validadas pelo ATR) e rompimento extremo na Banda Inferior de Bollinger (15m ou 1H) antes de cogitar uma entrada. Impede a compra de "facas caindo".

Auditoria Cognitiva (IA): Integração nativa com a API do Google Gemini. Após o filtro matemático, a IA atua como um Analista de Risco, avaliando o Price Action das últimas 12 horas, fluxo de volume e MACD para prever se o ativo tem força para atingir a meta de lucro nas próximas horas.

Gestão de Risco Dinâmica: Conta com Stop Dinâmico (calculado pelo ATR da moeda), Disaster Stop de proteção sistêmica e um Trailing Stop invisível para acompanhar o preço e maximizar o ganho no pico da alta.

Tribunal de Swap: Caso um ativo lateralize no prejuízo, a IA convoca um "Tribunal" matemático para avaliar se é estatisticamente viável assumir o loss atual e migrar para uma nova agulhada perfeita (Confiança > 95%).

Dashboard Transparente (Caixa Branca): Integrado ao painel.py, oferece controle UI do Desvio Padrão do Bollinger e do Cooldown em tempo real, além de um Dossiê completo detalhando as exatas métricas matemáticas calculadas pelo motor.

### default
A estratégia legada padrão. Baseia-se na teoria básica de saltar entre ativos analisando a proporção simples e variação de preço.

### multiple_coins
Variação da estratégia padrão projetada para manter o bot menos propenso a ficar "preso" em um único ativo durante correções, diluindo o risco de forma primária.