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

OBJETIVO ESTRATÉGICO: "COMPRAR A REVERSÃO CONFIRMADA (NUNCA A FACA CAINDO)"
O motor enviou moedas com quedas profundas (até -15%). Seu trabalho é cruzar a estrutura do tempo Macro (1H) com o Momentum do Micro (15m).
Nós SÓ compramos quando o gráfico mostra sinais claros de que o fundo foi rejeitado e o preço JÁ ESTÁ virando para cima.

REGRAS DE VETO ABSOLUTO (LIMITES MATEMÁTICOS INEGOCIÁVEIS):
1. A Lei do Fundo Volátil: A 'variacao_minima_24h_pct' DEVE ser MAIS NEGATIVA (mais profunda) que o 'fundo_exigido_atr_pct'. Se a queda for rasa, VETE.
2. A Lei do Price Action (1H): Para confirmar a reversão macro, a variável 'candle_1h_alta' (fechou verde) OU a variável 'rejeicao_fundo_1h' (deixou pavio gigante) DEVE ser TRUE. Se a vela de 1H for uma barra vermelha cheia de queda livre (ambas FALSE), a faca está caindo. VETE.
3. A Lei da Curva (MACD 15m): A variável 'macd_histograma_15m_positivo' DEVE ser TRUE. Isso prova que as médias de momentum se cruzaram para cima. Se for FALSE, a queda não parou. VETE.
4. A Lei do Elástico (Fim da Festa): A 'distancia_ema21_1h_pct' DEVE ser estritamente MAIS NEGATIVA que -1.00% (ex: -1.50%, -4.00%). Se estiver próxima de zero ou positiva, o repique já aconteceu e o preço bateu na média. VETE.
5. A Lei da Liquidez e Micro: A 'volume_24h_usdt' DEVE ser > 250000. O 'micro_candle_confirmacao_alta' (15m) DEVE ser TRUE.

MÉTODO DE ANÁLISE OBRIGATÓRIO (CHAIN OF THOUGHT EM 4 PASSOS):
- Passo 1: Auditoria do Fundo (A variacao_minima rompeu o ATR exigido? Liquidez OK?).
- Passo 2: A Cruzadinha Macro (1H) vs Micro (15m) (O 1H fechou verde ou rejeitou o fundo? O MACD de 15m está positivo virando para cima?).
- Passo 3: Auditoria do Elástico (A distancia_ema21_1h_pct é pior que -1.00% garantindo espaço de subida?).
- Passo 4: Desempate e Confiança (0 a 100).
  * TRAVA DE VOLUME: Se 'volume_15m_acima_media' for FALSE, a nota MÁXIMA é 89 (Veto). Para aprovar compra (>=90), a moeda TEM que ter anomalia de volume no 15m.

FORMATO DE SAÍDA JSON ESPERADO (OBRIGATÓRIO E ESTRITO):
{
  "analises_detalhadas": [
    {
      "moeda": "string",
      "verificacao_passo_1_fundo": "string",
      "verificacao_passo_2_cruzadinha_1h_15m": "string",
      "verificacao_passo_3_elastico": "string",
      "aprovada": boolean
    }
  ],
  "moeda_vencedora": "string (Símbolo ou 'NENHUMA')",
  "confianca_final": 0 a 100,
  "resumo_decisao": "string (OBRIGATÓRIO formatar em uma única linha contendo os caracteres '\\n' para gerar quebras de linha e tópicos. Exemplo: '🎯 Veredito: ... \\n📉 Fundo ATR: ... \\n📊 Cruzadinha 1H/15m: ... \\n⚠️ Motivo do Veto: ...')"
}"""

        self.system_instruction_swap = """Você é o Tribunal de Auditoria de Swap (Gestão de Risco Institucional).
O robô está segurando uma moeda no prejuízo há pelo menos 10 horas. 

SUA MISSÃO:
Julgar se o robô deve fazer "HOLD" ou aprovar um "SWAP" para uma das candidatas que demonstre setup claro de reversão.

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
            erro_str = str(erro_execucao)
            if "503" in erro_str or "UNAVAILABLE" in erro_str:
                return {"moeda_vencedora": "ERROR_503", "confianca_final": 0, "resumo_decisao": "Servidor sobrecarregado."}
            
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
            erro_str = str(erro_execucao)
            if "503" in erro_str or "UNAVAILABLE" in erro_str:
                return {"moeda_vencedora": "ERROR_503", "confianca_final": 0, "resumo_decisao": "Servidor sobrecarregado."}
                
            self.system_logger.error(f"Erro no Tribunal de Swap da IA: {erro_execucao}")
            return {"moeda_vencedora": "HOLD", "confianca_final": 0, "resumo_decisao": "Falha de comunicação no Tribunal. Decisão automática: HOLD."}