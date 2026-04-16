import json
from google import genai
from google.genai import types
from binance_trade_bot.config import Config

class MarketAnalyzer:
    """
    Comitê de Risco e Previsão Quantitativa Institucional.
    Atua APÓS o motor matemático ter filtrado as condições absolutas.
    """
    def __init__(self, logger):
        self.logger = logger
        self.config = Config()
        try:
            self.client = genai.Client(api_key=self.config.GOOGLE_API_KEY)
        except Exception as e:
            self.logger.error(f"Erro ao inicializar Google GenAI Client: {e}")
            self.client = None

    def _clean_payload_for_ai(self, batch_data):
        """ Higieniza o Dossiê para economizar tokens e focar a IA apenas em métricas preditivas """
        clean_batch = []
        for asset in batch_data:
            clean_asset = {
                "coin": asset["coin"],
                "current_price": asset["current_price"],
                "bollinger_touch_timeframe": asset.get("bollinger_touch_timeframe", "15m"),
                "volume_15m_pct": asset.get("volume_15m_pct", 100.0),
                "ema21_1h_distance_pct": asset.get("ema21_1h_distance_pct", "0%"),
                "change_24h_pct": asset.get("change_24h_pct", "0%"),
                "price_action_1h_last_12": asset.get("price_action_1h_last_12", []),
                "bullish_1h_candle": asset.get("bullish_1h_candle", False),
                "bottom_rejection_1h": asset.get("bottom_rejection_1h", False),
                "macd_1h_shifting_up": asset.get("macd_1h_shifting_up", False),
                "macd_histogram_1h_positive": asset.get("macd_histogram_1h_positive", False),
                "macd_histogram_15m_positive": asset.get("macd_histogram_15m_positive", False),
                "bullish_15m_micro_candle": asset.get("bullish_15m_micro_candle", False),
                "rsi_MACRO_4h": asset.get("rsi_MACRO_4h", 50.0),
                "rsi_INTER_1h": asset.get("rsi_INTER_1h", 50.0),
                "rsi_MICRO_15m": asset.get("rsi_MICRO_15m", 50.0)
            }
            clean_batch.append(clean_asset)
        return clean_batch

    def analyze_batch(self, batch_data):
        if not self.client:
            return {"winning_coin": "ERROR_503", "final_confidence": 0, "decision_summary": "API Client not initialized."}
        
        clean_batch = self._clean_payload_for_ai(batch_data)
        
        prompt = f"""
        Você é um Analista Quantitativo Institucional Sênior avaliando um lote de criptomoedas para Swing Trade curto.
        As moedas deste JSON já passaram por um rigoroso filtro algorítmico.
        Assuma como FATO que TODAS as moedas apresentadas possuem liquidez suficiente (Volume), queda esticada (EMA) e toque extremo em fundo (Bollinger).

        === REGRAS INQUEBRÁVEIS ===
        REGRA 1: PROIBIÇÃO DE VETO MATEMÁTICO: Não rejeite moedas alegando regras matemáticas primárias (ex: falta de liquidez ou distância de EMA). Seu foco é a Previsão Analítica (Predictive Analytics).
        REGRA 2: FOCO NA REVERSÃO: Você busca uma estrutura com "Exaustão Vendedora" confirmada e iminente repique de alta para atingir +2.00% em 14h. Não compre facas caindo sem freio.
        REGRA 3: EXIGÊNCIA DE CONFIANÇA: Para aprovar uma compra, a "final_confidence" DEVE ser maior ou igual a 90. Se o risco for alto demais, o vencedor DEVE ser "NENHUMA".

        === PASSOS DE EXECUÇÃO ===
        PASSO 1: CONTEXTO MACRO (Price Action 12h)
        Analise o array `price_action_1h_last_12`. A moeda está consolidando um fundo lateral após a queda, ou os candles continuam derretendo agressivamente? Priorize a absorção de queda.

        PASSO 2: O PESO DO FUNDO (Bollinger Context)
        Avalie o `bollinger_touch_timeframe`. Se a moeda furou as bandas de "15m + 1H" simultaneamente, a probabilidade de um repique violento é exponencialmente maior do que apenas "15m".

        PASSO 3: MOMENTUM E GATILHO (MACD e Absorção)
        Verifique a confluência de momentum: O MACD de 1H está virando para cima (`macd_1h_shifting_up`)? O MACD 15m está apontando aceleração (`macd_histogram_15m_positive`)? Há defesa compradora (`bottom_rejection_1h`)?

        PASSO 4: VEREDITO
        Cruze as informações dos Passos 1, 2 e 3. Escolha a única moeda com a estrutura mais explosiva para o repique, ou declare "NENHUMA".
        
        Retorne ESTRITAMENTE o formato JSON nativo, sem marcações markdown de bloco de código (```json):
        {{
            "winning_coin": "TICKER_AQUI",
            "final_confidence": 0 a 100,
            "decision_summary": "Seu parecer analítico justificando a previsão através do Price Action, Momentum e Contexto de Fundo."
        }}
        
        DADOS DO LOTE (Higienizado e Pré-Filtrado):
        {json.dumps(clean_batch, indent=2)}
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            self.logger.error(f"Erro na IA: {e}")
            return {"winning_coin": "ERROR_503", "final_confidence": 0, "decision_summary": f"Falha de comunicacao com API: {e}"}

    def analyze_swap(self, batch_data, current_coin, drop_pct, locked_hours):
        if not self.client:
            return {"winning_coin": "ERROR_503", "final_confidence": 0, "decision_summary": "API Client not initialized."}
        
        clean_batch = self._clean_payload_for_ai(batch_data)
        
        prompt = f"""
        Você é o Tribunal de Risco Institucional avaliando um SWAP de Reversão de Média.
        A operação atual ({current_coin}) está presa em carteira há {locked_hours:.1f}h acumulando um rebaixamento de {drop_pct:.2f}%.
        As moedas candidatas no JSON já foram validadas pelo motor matemático e possuem liquidez, extensão e toque no fundo do Bollinger adequados.

        === REGRAS DO TRIBUNAL ===
        REGRA 1: MIGRAÇÃO DE EXTREMO RISCO: Você só deve aprovar a troca se a candidata tiver uma configuração de reversão inegavelmente superior à operação atual.
        REGRA 2: CONFIANÇA MÁXIMA: A "final_confidence" na candidata DEVE ser MAIOR OU IGUAL a 95 para justificar a realização do prejuízo atual de {drop_pct:.2f}%. Caso contrário, a decisão é "HOLD".

        === PASSOS DE EXECUÇÃO ===
        PASSO 1: AVALIAR ESTRUTURA MACRO: Analise o `price_action_1h_last_12` da candidata. Ela formou um fundo sólido em exaustão?
        PASSO 2: PESO DO BOLLINGER: Priorize candidatas cujo `bollinger_touch_timeframe` seja forte (ex: "15m + 1H").
        PASSO 3: MOMENTUM: Confirme se a aceleração (`macd_1h_shifting_up`, `macd_histogram_15m_positive`) suporta uma retomada rápida.

        Retorne ESTRITAMENTE o JSON nativo, sem marcações markdown:
        {{
            "winning_coin": "TICKER_OU_HOLD",
            "final_confidence": 0 a 100,
            "decision_summary": "Justificativa preditiva cruzando Price Action e Momentum para validar o swap ou manter a operação."
        }}
        
        DADOS DO LOTE CANDIDATO:
        {json.dumps(clean_batch, indent=2)}
        """
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            self.logger.error(f"Erro na IA Swap: {e}")
            return {"winning_coin": "ERROR_503", "final_confidence": 0, "decision_summary": f"Falha de comunicacao com API: {e}"}