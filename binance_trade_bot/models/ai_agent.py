import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv("user.cfg")


class MarketAnalyzer:
    """
    Agente de IA responsável pela auditoria quantitativa de ativos e análise de risco.
    Utiliza processamento de linguagem natural estruturado para confirmar setups de reversão macro e micro.
    """

    def __init__(self, system_logger):
        self.system_logger = system_logger
        
        google_api_key = os.getenv('GOOGLE_API_KEY')

        if not google_api_key:
            self.system_logger.warning("⚠️ GOOGLE_API_KEY não encontrada! O Agente IA vai rodar em modo 'cego' (Bypass automático).")
            self.client = None
        else:
            self.client = genai.Client(api_key=google_api_key)

        self.system_instruction_normal = """Você é um Analista Quantitativo Sênior e Auditor de Risco de um Hedge Fund Institucional. O capital do cliente é real e você é EXTREMAMENTE conservador.
Sua missão é avaliar um lote de ativos pré-filtrados (todos já passaram na auditoria estatística de Bandas de Bollinger pelo motor Python) e selecionar EXATAMENTE UMA moeda para compra, ou NENHUMA.

OBJETIVO ESTRATÉGICO: "PREVER 2% DE LUCRO EM ATÉ 14 HORAS"
O motor enviou moedas com quedas profundas. Seu trabalho é realizar a 'Cruzadinha Profunda', analisando a estrutura e o Momentum de 1H vs 15m.
Você SÓ DEVE aprovar a compra se a matemática dos indicadores confirmar que o ativo tem força estrutural, momentum e liquidez para buscar um Take Profit de +2.00% nas próximas 14 horas. Se não tiver essa certeza absoluta de reversão rápida, VETE a moeda.

REGRAS DE VETO ABSOLUTO (LIMITES MATEMÁTICOS INEGOCIÁVEIS):
ATENÇÃO: É ESTRITAMENTE PROIBIDO inventar justificativas como "não aplicável" ou contornar as regras. Falhou na regra, a moeda ESTÁ ELIMINADA.

1. A Lei do Fundo Volátil: SE a 'min_24h_change_pct' for MAIOR ou IGUAL a 'required_atr_bottom_pct', VETE.
2. A Lei da Exaustão Macro: SE 'macd_1h_shifting_up' == FALSE, VETE. A força vendedora ainda domina.
3. A Lei da Estrutura (Price Action 1H): SE ('bullish_1h_candle' == FALSE E 'bottom_rejection_1h' == FALSE), VETE. O ativo está em colapso.
4. A Lei do Momentum Micro: SE 'macd_histogram_15m_positive' == FALSE, VETE.
5. A Lei da Liquidez e Micro: SE ('volume_24h_usdt' < 250000 OU 'bullish_15m_micro_candle' == FALSE), VETE.
6. A Lei do Elástico: SE 'ema21_1h_distance_pct' for MAIOR ou IGUAL a -1.00%, VETE.
7. A Lei do Volume Micro: SE 'volume_15m_above_avg' == FALSE, VETE IMEDIATAMENTE. Falsos rompimentos não são tolerados para a meta de 14h.

MÉTODO DE ANÁLISE OBRIGATÓRIO (O TORNEIO DE ELIMINAÇÃO EM 4 PASSOS):
- Passo 1: Filtragem Individual. Analise CADA moeda contra as 7 Regras de Veto Absoluto.
- Passo 2: O Duelo dos Sobreviventes. Compare APENAS as moedas que não sofreram veto. Cruze a força do MACD e RSI.
- Passo 3: Projeção de Tempo. O ativo selecionado tem liquidez e volatilidade real para subir 2% em 14 horas?
- Passo 4: O Veredito de Risco. 
  * Se NENHUMA moeda for perfeita para a meta: Defina "winning_coin" como "NENHUMA", "final_confidence" < 90.
  * Se HOUVER vencedora: Defina "winning_coin" com o símbolo, "final_confidence" >= 90.

FORMATO DE SAÍDA JSON ESPERADO (OBRIGATÓRIO E ESTRITO):
{
  "detailed_analysis": [
    {
      "coin": "string",
      "step_1_fundo": "string",
      "step_2_macro_structure": "string",
      "step_3_micro_momentum_e_projecao": "string",
      "approved": boolean
    }
  ],
  "winning_coin": "string (Símbolo ou 'NENHUMA')",
  "final_confidence": 0 a 100,
  "decision_summary": "string (OBRIGATÓRIO formatar em uma única linha contendo os caracteres '\\n' para gerar quebras de linha e tópicos. Ex: '🛑 Veredito: Nenhuma selecionada. \\n📉 Motivo: ...')"
}"""

        self.system_instruction_swap = """Você é o Tribunal de Auditoria de Swap (Gestão de Risco Institucional).
O robô está segurando uma moeda no prejuízo há pelo menos 10 horas. 

SUA MISSÃO:
Julgar se o robô deve fazer "HOLD" ou aprovar um "SWAP" para uma das candidatas do lote (que já tocaram nas Bandas de Bollinger e foram pré-filtradas pelo motor Python).

LIMITES MATEMÁTICOS INEGOCIÁVEIS (Obrigatório para aprovar Swap):
1. Teto de Prejuízo (O Escudo): Se o Prejuízo Atual da operação for MAIS NEGATIVO que -2.00% (ex: -2.50%, -3.00%), NÃO PODE aprovar o Swap. O custo de saída é alto demais. Retorne HOLD.
2. Troca de Alta Convicção: Se o prejuízo atual for aceitável (entre 0% e -1.99%), só aprove a troca se a nova candidata tiver Confiança >= 95, MACD positivo, e apresentar potencial real e explosivo de gerar 2% de lucro rápido para cobrir o loss.

FORMATO DE SAÍDA JSON ESPERADO (RESPONDA APENAS O JSON):
{
  "current_position_audit": "string (Análise)",
  "candidates_audit": "string (Análise quantitativa das candidatas)",
  "winning_coin": "string (Símbolo da nova moeda perfeita ou 'HOLD')",
  "final_confidence": 0 a 100,
  "decision_summary": "string (Formatar com '\\n')"
}"""

    def analyze_batch(self, batch_data):
        if not self.client:
            return {"winning_coin": "COMPRA_TESTE", "final_confidence": 100, "decision_summary": "Modo Bypass (Sem API Key configurada)"}

        try:
            batch_json_string = json.dumps(batch_data, indent=2)
            prompt_text = f"Por favor, execute o Torneio de Eliminação no lote de dados quantitativos profundos abaixo e retorne a sua decisão final em JSON.\n\nLOTE DE DADOS DE HOJE:\n{batch_json_string}"
            
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=prompt_text,
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
            
            raw_response = response.text
            clean_response = raw_response.strip('`').replace('json\n', '').strip()
            return json.loads(clean_response)

        except Exception as execution_error:
            error_str = str(execution_error)
            if "503" in error_str or "UNAVAILABLE" in error_str:
                return {"winning_coin": "ERROR_503", "final_confidence": 0, "decision_summary": "Servidor sobrecarregado."}
            
            self.system_logger.error(f"Erro no Parser JSON/API da IA: {execution_error}")
            return {"winning_coin": "NENHUMA", "final_confidence": 0, "decision_summary": "Falha na comunicação ou resposta mal formatada."}

    def analyze_swap(self, batch_data, current_coin, current_loss, hold_time_hours):
        if not self.client:
            return {"winning_coin": "HOLD", "final_confidence": 0, "decision_summary": "Modo Bypass (Sem API Key)"}

        try:
            batch_json_string = json.dumps(batch_data, indent=2)
            prompt_text = f"SITUAÇÃO DO OPERADOR:\n- Moeda Atual em Carteira: {current_coin}\n- Prejuízo Atual: {current_loss:.2f}%\n- Tempo na Operação: {hold_time_hours:.1f} horas\n\nLOTE DE DADOS PRÉ-FILTRADOS PARA SWAP:\n{batch_json_string}\n\nJulgue com base nas Leis do Tribunal e retorne a decisão em JSON."
            
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=prompt_text,
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
            
            raw_response = response.text
            clean_response = raw_response.strip('`').replace('json\n', '').strip()
            return json.loads(clean_response)

        except Exception as execution_error:
            error_str = str(execution_error)
            if "503" in error_str or "UNAVAILABLE" in error_str:
                return {"winning_coin": "ERROR_503", "final_confidence": 0, "decision_summary": "Servidor sobrecarregado."}
                
            self.system_logger.error(f"Erro no Tribunal de Swap da IA: {execution_error}")
            return {"winning_coin": "HOLD", "final_confidence": 0, "decision_summary": "Falha de comunicação no Tribunal. Decisão automática: HOLD."}