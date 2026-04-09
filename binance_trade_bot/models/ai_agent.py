import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv


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
Sua missão é avaliar um lote de ativos pré-filtrados e selecionar EXATAMENTE UMA moeda para compra, ou NENHUMA se o mercado estiver perigoso.

OBJETIVO ESTRATÉGICO: "COMPRAR A REVERSÃO CONFIRMADA (NUNCA A FACA CAINDO)"
O motor enviou moedas com quedas profundas. Seu trabalho é realizar a 'Cruzadinha Profunda', analisando a estrutura/Momentum de 1H vs estrutura/Momentum de 15m.
Não compre repiques de 'dead cat bounce'. Só aprove a compra se a força vendedora do 1H estiver exausta E o 15m confirmar entrada de capital.

REGRAS DE VETO ABSOLUTO (LIMITES MATEMÁTICOS INEGOCIÁVEIS - FALHOU EM UM, ESTÁ ELIMINADA):
1. A Lei do Fundo Volátil: A 'min_24h_change_pct' DEVE ser MAIS NEGATIVA que o 'required_atr_bottom_pct'. Se a queda for rasa, VETE.
2. A Lei da Agulhada de Bollinger (Exaustão Estatística): É OBRIGATÓRIO que a variável 'touched_lower_band_15m' seja TRUE OU a 'touched_lower_band_1h' seja TRUE. Se AMBAS vierem como FALSE, o ativo não furou o desvio padrão. VETE IMEDIATAMENTE.
3. A Lei da Exaustão Macro (1H MACD): A variável 'macd_1h_shifting_up' DEVE ser TRUE. Se for FALSE, a faca ainda está caindo. VETE.
4. A Lei da Estrutura (Price Action 1H - Últimas 12h): Analise o array 'price_action_1h_last_12'. Se o ativo estiver fazendo fundos consistentemente mais baixos de forma violenta E a 'bullish_1h_candle' for FALSE, o ativo está em colapso. VETE. (Releve a estrutura de baixa APENAS se 'bottom_rejection_1h' for TRUE).
5. A Lei do Momentum Micro (15m): A variável 'macd_histogram_15m_positive' DEVE ser TRUE. O fluxo de curto prazo já precisa ser comprador. Se for FALSE, VETE.
6. A Lei da Liquidez e Micro: A 'volume_24h_usdt' DEVE ser > 250000. O 'bullish_15m_micro_candle' DEVE ser TRUE.
7. A Lei do Elástico: A 'ema21_1h_distance_pct' DEVE ser estritamente MAIS NEGATIVA que -1.00%.
8. A Lei do Volume Micro: A variável 'volume_15m_above_avg' DEVE ser TRUE para confirmar a entrada de capital institucional.

MÉTODO DE ANÁLISE OBRIGATÓRIO (O TORNEIO DE ELIMINAÇÃO EM 3 PASSOS):
- Passo 1: Filtragem Individual. Analise os dados de CADA moeda do lote contra TODAS as 8 Regras de Veto Absoluto.
- Passo 2: O Duelo dos Sobreviventes. Compare APENAS as moedas que passaram 100% no Passo 1. Busque aquela com a melhor assimetria (Agulhada em Bollinger validada + MACD forte).
- Passo 3: O Veredito de Risco. 
  * Se NENHUMA moeda sobreviveu ao Passo 1: Você DEVE definir "winning_coin" como "NENHUMA", "final_confidence" < 90, e o "decision_summary" DEVE iniciar com "🛑 Nenhuma moeda selecionada. Todas falharam em ao menos um requisito" e explicar o motivo predominante das reprovações.
  * Se HOUVER uma vencedora perfeita: Defina "winning_coin" com o símbolo, "final_confidence" >= 90, e explique o motivo da vitória no resumo.

FORMATO DE SAÍDA JSON ESPERADO (OBRIGATÓRIO E ESTRITO):
{
  "detailed_analysis": [
    {
      "coin": "string",
      "step_1_fundo_e_bollinger": "string",
      "step_2_macro_structure": "string",
      "step_3_micro_momentum": "string",
      "approved": boolean
    }
  ],
  "winning_coin": "string (Símbolo ou 'NENHUMA')",
  "final_confidence": 0 a 100,
  "decision_summary": "string (OBRIGATÓRIO formatar em uma única linha contendo os caracteres '\\n' para gerar quebras de linha e tópicos. Ex: '🛑 Veredito: Nenhuma moeda selecionada. \\n📉 Motivo: ... \\n📉 Bollinger: ...')"
}"""

        self.system_instruction_swap = """Você é o Tribunal de Auditoria de Swap (Gestão de Risco Institucional).
O robô está segurando uma moeda no prejuízo há pelo menos 10 horas. 

SUA MISSÃO:
Julgar se o robô deve fazer "HOLD" ou aprovar um "SWAP" para uma das candidatas do lote.

LIMITES MATEMÁTICOS INEGOCIÁVEIS (Obrigatório para aprovar Swap):
1. Teto de Prejuízo (O Escudo): Se o Prejuízo Atual da operação for MAIS NEGATIVO que -2.00% (ex: -2.50%, -3.00%), NÃO PODE aprovar o Swap. O custo de saída é alto demais. Retorne HOLD.
2. Troca Desproporcional e Bollinger: Se o prejuízo atual estiver entre 0% e -1.99%, você SÓ PODE aprovar a troca se a nova moeda candidata tiver Confiança >= 95. Para atingir essa nota, a candidata TEM QUE ter tocado na banda de Bollinger inferior ('touched_lower_band_15m' == TRUE ou 'touched_lower_band_1h' == TRUE) e possuir MACD 15m positivo.

FORMATO DE SAÍDA JSON ESPERADO (RESPONDA APENAS O JSON):
{
  "current_position_audit": "string (Análise)",
  "candidates_audit": "string (Análise das candidatas cruzando com as Regras de Bollinger)",
  "winning_coin": "string (Símbolo da nova moeda perfeita ou 'HOLD')",
  "final_confidence": 0 a 100,
  "decision_summary": "string (Formatar com '\\n')"
}"""

    def analyze_batch(self, batch_data):
        if not self.client:
            return {"winning_coin": "COMPRA_TESTE", "final_confidence": 100, "decision_summary": "Modo Bypass (Sem API Key configurada)"}

        try:
            batch_json_string = json.dumps(batch_data, indent=2)
            prompt_text = f"Por favor, execute a Análise em 4 Passos no lote de dados quantitativos profundos (contexto 12h e Bandas de Bollinger) abaixo e retorne a sua decisão final em JSON.\n\nLOTE DE DADOS DE HOJE:\n{batch_json_string}"
            
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