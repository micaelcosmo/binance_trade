import os
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.output_parser import StrOutputParser

class MarketAnalyzer:
    def __init__(self, logger):
        self.logger = logger
        
        # Puxa a chave diretamente das variáveis de ambiente ou arquivo .env
        api_key = os.getenv('GOOGLE_API_KEY')

        if not api_key:
            self.logger.warning("⚠️ GOOGLE_API_KEY não encontrada! O Agente IA vai rodar em modo 'cego' (Bypass automático).")
            self.language_model = None
        else:
            self.language_model = ChatGoogleGenerativeAI(
                model="gemini-1.5-flash",
                google_api_key=api_key,
                temperature=0.1, 
                model_kwargs={"response_mime_type": "application/json"}
            )

        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """Você é um Trader Institucional Sênior de criptomoedas, especialista em Price Action, microestruturas e análise de momento.
            Sua missão é analisar dados técnicos recentes e prever a probabilidade de um falso rompimento (topo) ou de uma reversão de tendência.

            REGRAS RÍGIDAS:
            1. Responda EXCLUSIVAMENTE em formato JSON válido. Sem formatação markdown ou textos extras.
            2. A 'recomendacao' deve ser estritamente: "COMPRAR" ou "AGUARDAR".
            3. A 'confianca' deve ser um inteiro de 0 a 100.
            4. O 'motivo' deve ter no máximo 2 frases curtas e diretas, explicando a leitura dos candles.

            Formato esperado:
            {"recomendacao": "COMPRAR", "confianca": 85, "motivo": "Candles de força com volume crescente confirmam o rompimento da média. Risco de falso topo é baixo."}"""),
            
            ("human", """Aqui estão os dados técnicos do par {moeda_alvo} (resumo):
            - Preço Atual: {preco_atual}
            - RSI Atual (14): {rsi_atual}
            - Variação 4H: {variacao_4h}%
            - Tendência EMA (9x21): Confirmada Alta

            Dados brutos dos últimos 5 candles (Timestamp, Open, High, Low, Close, Volume):
            {dados_candles}

            Analise a ação de preço destes últimos candles. O mercado demonstra força real de compra ou é um topo de exaustão? Qual a sua recomendação de ação agora?""")
        ])

        if self.language_model:
            self.processing_chain = self.prompt_template | self.language_model | StrOutputParser()

    def analisar(self, moeda_alvo, preco_atual, rsi_atual, variacao_4h, dataframe_candles):
        if not self.language_model:
            return {"recomendacao": "COMPRAR", "confianca": 100, "motivo": "Modo Bypass (Sem API Key configurada)"}

        try:
            dataframe_recent_candles = dataframe_candles.tail(5)[['timestamp', 'open', 'high', 'low', 'close', 'vol']]
            candles_string_format = dataframe_recent_candles.to_string(index=False)

            self.logger.info(f"🧠 Consultando Oráculo IA (Gemini) para {moeda_alvo}...")
            
            resposta_bruta = self.processing_chain.invoke({
                "moeda_alvo": moeda_alvo,
                "preco_atual": preco_atual,
                "rsi_atual": f"{rsi_atual:.2f}",
                "variacao_4h": f"{variacao_4h:.2f}",
                "dados_candles": candles_string_format
            })

            resposta_limpa = resposta_bruta.strip('`').replace('json\n', '').strip()
            resposta_json = json.loads(resposta_limpa)
            
            return resposta_json

        except Exception as erro_execucao:
            self.logger.error(f"Erro no Agente IA: {erro_execucao}")
            return {"recomendacao": "AGUARDAR", "confianca": 0, "motivo": "Falha na comunicação com a API."}
    