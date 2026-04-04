import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv


load_dotenv("user.cfg")


class MarketAnalyzer:
    def __init__(self, system_logger):
        self.system_logger = system_logger
        
        google_api_key = os.getenv('GOOGLE_API_KEY')

        if not google_api_key:
            self.system_logger.warning("⚠️ GOOGLE_API_KEY não encontrada! O Agente IA vai rodar em modo 'cego' (Bypass automático).")
            self.client = None
        else:
            self.client = genai.Client(api_key=google_api_key)

        self.system_instruction_normal = """Você é um Analista Quantitativo Sênior e Auditor de Risco de um Hedge Fund Institucional.
Sua missão é avaliar um lote de ativos pré-filtrados e selecionar EXATAMENTE UMA moeda para compra, ou NENHUMA.

OBJETIVO ESTRATÉGICO: "REVERSÃO À MÉDIA (MEAN REVERSION) PARA SWING DE 8H A 14H"
O motor Python enviou moedas que sofreram um 'sell-off' comprovado pelo ATR.
Sua função é auditar a Curva de Reversão através do cruzamento MACD de 15m e do distanciamento da EMA de 1H. Nós não compramos facas caindo, nós compramos a confirmação da barriga da reversão.

REGRAS DE VETO ABSOLUTO (LIMITES MATEMÁTICOS INEGOCIÁVEIS):
Você é expressamente proibido de aprovar moedas que violem estas regras:
1. A Lei do Fundo Volátil: A 'variacao_minima_24h_pct' DEVE ser MAIS NEGATIVA (mais profunda) que o 'fundo_exigido_atr_pct'. Se a queda foi rasa (ex: a moeda caiu apenas -1.00% quando o exigido era -2.00%), VETE imediatamente.
2. A Lei da Curva (MACD): A variável 'macd_histograma_15m_positivo' DEVE ser estritamente TRUE. Isso prova que as médias de momentum se cruzaram e a tendência de 15m virou para alta. Se for FALSE, a faca ainda está caindo. VETE.
3. A Lei do Micro (15m): A variável 'micro_candle_confirmacao_alta' no 15m DEVE ser TRUE. Sem candle verde estrutural, VETE.
4. A Lei do Elástico (Fim da Festa): A 'distancia_ema21_1h_pct' DEVE ser estritamente MAIS NEGATIVA que -1.00% (ex: -1.50%, -4.00%). Se estiver próxima de zero ou positiva, o elástico já retornou à média e o repique acabou. VETE.
5. A Lei da Liquidez: A 'volume_24h_usdt' DEVE ser > 250000. Se menor, VETE.
6. A Lei do Desastre Macro: Se o 'rsi_MACRO_4h' estiver abaixo de 20.00 sem nenhum sinal de freio, é um colapso semanal. Evite.

MÉTODO DE ANÁLISE OBRIGATÓRIO (CHAIN OF THOUGHT EM 4 PASSOS):
Para cada moeda no lote, documente no JSON:

- Passo 1: Auditoria de Queda e Liquidez (A variacao_minima rompeu o ATR exigido? Liquidez > 250k?).
- Passo 2: Auditoria Macro e Elasticidade (O RSI de 4H/1H suporta repique? A distancia_ema21_1h_pct é pior que -1.00%?).
- Passo 3: Auditoria da Curva de Reversão (O macd_histograma_15m_positivo é TRUE confirmando a barriga? O candle de 15m fechou em alta?).
- Passo 4: Desempate e Confiança (0 a 100).
  * TRAVA DE VOLUME: Se 'volume_15m_acima_media' for FALSE, a nota MÁXIMA é 89 (Veto). Para aprovar compra (>=90), é MATEMATICAMENTE OBRIGATÓRIO que a moeda tenha anomalia de volume institucional no 15m (TRUE).

FORMATO DE SAÍDA JSON ESPERADO (OBRIGATÓRIO E ESTRITO):
{
  "analises_detalhadas": [
    {
      "moeda": "string",
      "verificacao_passo_1_queda_e_liquidez": "string",
      "verificacao_passo_2_macro_elasticidade": "string",
      "verificacao_passo_3_curva_macd_15m": "string",
      "aprovada": boolean
    }
  ],
  "moeda_vencedora": "string (Símbolo ou 'NENHUMA')",
  "confianca_final": 0 a 100,
  "resumo_decisao": "string (OBRIGATÓRIO formatar em uma única linha contendo os caracteres '\\n' para gerar quebras de linha e tópicos. Exemplo: '🎯 Veredito: ... \\n📉 Fundo ATR & Liquidez: ... \\n📊 Curva MACD & EMA: ... \\n⚠️ Motivo do Veto: ...')"
}"""

        self.system_instruction_swap = """Você é o Tribunal de Auditoria de Swap (Gestão de Risco Institucional).
O robô está segurando uma moeda no prejuízo. O stop loss matemático do motor é duro (máximo de -3.50%). 

SUA MISSÃO:
Julgar se o robô deve fazer "HOLD" (aguardar recuperação parcial) ou aprovar um "SWAP DE EMERGÊNCIA" caso exista uma oportunidade absurdamente superior.

LIMITES MATEMÁTICOS INEGOCIÁVEIS:
1. Teto de Prejuízo (O Escudo): Se o Prejuízo Atual for MAIS NEGATIVO que -2.00% (ex: -2.50%, -3.00%), NÃO PODE aprovar o Swap. O custo é alto demais. Retorne HOLD.
2. Troca Desproporcional: Se o prejuízo atual está em zona aceitável (0% a -1.99%), só aprove se a nova moeda tiver Confiança >= 95.

FORMATO DE SAÍDA JSON ESPERADO (RESPONDA APENAS O JSON):
{
  "auditoria_posicao_atual": "string (Análise)",
  "auditoria_candidatas": "string (Análise das candidatas no lote)",
  "moeda_vencedora": "string (Símbolo da nova moeda perfeita ou 'HOLD')",
  "confianca_final": 0 a 100,
  "resumo_decisao": "string (Formatar com '\\n')"
}"""

    def analisar_lote(self, lote_dados):
        if not self.client:
            return {"moeda_vencedora": "COMPRA_TESTE", "confianca_final": 100, "resumo_decisao": "Modo Bypass (Sem API Key configurada)"}

        try:
            lote_json_string = json.dumps(lote_dados, indent=2)
            prompt_texto = f"Por favor, execute a Análise em 4 Passos no lote de dados abaixo e retorne a sua decisão final em JSON.\n\nLOTE DE DADOS DE HOJE:\n{lote_json_string}"
            
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=prompt_texto,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction_normal,
                    temperature=0.1,
                    max_output_tokens=8192,
                    response_mime_type="application/json",
                )
            )

            usage = response.usage_metadata
            if usage:
                tokens_in = getattr(usage, 'prompt_token_count', 0)
                tokens_out = getattr(usage, 'candidates_token_count', 0)
                total_tokens = getattr(usage, 'total_token_count', 0)
                self.system_logger.info(f"📊 [API AUDIT] Tokens (Caça Diária) -> Input: {tokens_in} | Output: {tokens_out} | Total: {total_tokens}")
            
            resposta_bruta = response.text
            resposta_limpa = resposta_bruta.strip('`').replace('json\n', '').strip()
            return json.loads(resposta_limpa)

        except Exception as erro_execucao:
            self.system_logger.error(f"Erro no Parser JSON/API da IA: {erro_execucao}")
            return {"moeda_vencedora": "NENHUMA", "confianca_final": 0, "resumo_decisao": "Falha na comunicação ou resposta mal formatada."}

    def analisar_swap(self, lote_dados, moeda_atual, prejuizo_atual, tempo_preso_horas):
        if not self.client:
            return {"moeda_vencedora": "HOLD", "confianca_final": 0, "resumo_decisao": "Modo Bypass (Sem API Key)"}

        try:
            lote_json_string = json.dumps(lote_dados, indent=2)
            prompt_texto = f"SITUAÇÃO DO OPERADOR:\n- Moeda Atual em Carteira: {moeda_atual}\n- Prejuízo Atual: {prejuizo_atual:.2f}%\n- Tempo na Operação: {tempo_preso_horas:.1f} horas\n\nLOTE DE DADOS PRÉ-FILTRADOS PARA SWAP:\n{lote_json_string}\n\nJulgue com base nas Leis do Tribunal e retorne a decisão em JSON."
            
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=prompt_texto,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction_swap,
                    temperature=0.1,
                    max_output_tokens=4096,
                    response_mime_type="application/json",
                )
            )

            usage = response.usage_metadata
            if usage:
                tokens_in = getattr(usage, 'prompt_token_count', 0)
                tokens_out = getattr(usage, 'candidates_token_count', 0)
                self.system_logger.info(f"⚖️ [API AUDIT] Tokens (Tribunal de Swap) -> Total: {tokens_in + tokens_out}")
            
            resposta_bruta = response.text
            resposta_limpa = resposta_bruta.strip('`').replace('json\n', '').strip()
            return json.loads(resposta_limpa)

        except Exception as erro_execucao:
            self.system_logger.error(f"Erro no Tribunal de Swap da IA: {erro_execucao}")
            return {"moeda_vencedora": "HOLD", "confianca_final": 0, "resumo_decisao": "Falha de comunicação no Tribunal. Decisão automática: HOLD."}