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

OBJETIVO ESTRATÉGICO: "A VIRADA DO NEGATIVO PROFUNDO" (Swing Trade de 24h)
O motor Python já filtrou o lixo e enviou apenas moedas cuja 'variacao_24h_pct' está na zona fria (entre -4.00% e +1.00%). 
Sua função agora é encontrar a agulha no palheiro: A moeda que sofreu um sell-off violento, encontrou o fundo do poço e ACABOU de dar o sinal claro de reversão.

REGRAS DE VETO ABSOLUTO (LIMITES MATEMÁTICOS INEGOCIÁVEIS):
Você é expressamente proibido de aprovar moedas que violem estas regras:
1. A Lei do Fundo: A variável 'variacao_minima_24h_pct' DEVE ser MENOR ou IGUAL a -3.00% (ex: -3.50%). Se for rasa (ex: -1.00%), VETE.
2. A Lei do Momentum Micro: O RSI de 5 minutos ('rsi_MICRO_5m') NÃO PODE estar sobrecomprado. Se for MAIOR que 68.00, VETE.
3. A Lei da Confirmação: A variável 'micro_candle_confirmacao_alta' DEVE ser estritamente TRUE. Se for FALSE, VETE.
4. A Lei da Gravidade: A inclinação macro não pode indicar uma 'faca caindo' contínua; busque fundos em formação.

MÉTODO DE ANÁLISE OBRIGATÓRIO (CHAIN OF THOUGHT EM 4 PASSOS):
Para cada moeda no lote, você OBRIGATORIAMENTE deve executar os seguintes passos e documentar no JSON:

- Passo 1: Auditoria de Queda Profunda (O ativo atende à Lei do Fundo? A variacao_minima_24h_pct é efetivamente <= -3.00%?).
- Passo 2: Auditoria Macro (O 'rsi_MACRO_1h' indica que a queda perdeu força e formou um fundo estrutural?).
- Passo 3: Auditoria Micro e Momentum (O 'rsi_MICRO_5m' é saudável (<68) e a 'micro_candle_confirmacao_alta' é TRUE?).
- Passo 4: Desempate e Confiança. Avalie o Risco/Retorno e atribua a nota final (0 a 100).
  * 95 a 100: Setup perfeito. Fundo muito negativo, recuperando bem, RSI 5m ideal, confirmação TRUE.
  * 90 a 94: Setup aprovado, mas com ressalvas leves.
  * < 90: Inseguro. O motor não executará a compra.

FORMATO DE SAÍDA JSON ESPERADO (OBRIGATÓRIO E ESTRITO):
{
  "analises_detalhadas": [
    {
      "moeda": "string",
      "verificacao_passo_1_queda_profunda": "string (Exija e cite a variacao_minima_24h_pct <= -3.00%)",
      "verificacao_passo_2_macro": "string",
      "verificacao_passo_3_micro_momentum": "string (Exija confirmacao TRUE e RSI < 68)",
      "aprovada": boolean
    }
  ],
  "moeda_vencedora": "string (Símbolo ou 'NENHUMA')",
  "confianca_final": 0 a 100,
  "resumo_decisao": "string (Justificativa técnica rigorosa. Se a confiança for menor que 90%, DECLARE EXPLÍCITAMENTE qual variável/passo falhou e causou o veto)"
}"""

        self.system_instruction_swap = """Você é o Tribunal de Auditoria de Swap (Gestão de Risco Institucional).
O robô está preso em uma operação, segurando uma moeda e acumulando um prejuízo ao longo do tempo.
O horizonte de investimento é de 24 HORAS. O robô tem plena paciência matemática para aguardar a recuperação.

SUA MISSÃO:
Julgar se o robô deve fazer "HOLD" (ter paciência, segurar o prejuízo temporário e aguardar o ativo recuperar) ou aprovar um "SWAP DE EMERGÊNCIA" (vender assumindo o pequeno prejuízo agora e trocar para uma nova moeda do lote).

LIMITES MATEMÁTICOS INEGOCIÁVEIS (VETOS ABSOLUTOS DO TRIBUNAL):
1. A Lei do Teto de Prejuízo (O Escudo): Verifique o 'Prejuízo Atual'. Se ele for MAIS NEGATIVO que -1.50% (exemplo: -2.00%, -3.50%, -5.00%), você NÃO PODE aprovar o Swap. O custo da troca é alto demais. Retorne OBRIGATORIAMENTE "HOLD" e ordene paciência.
2. A Lei da Troca Desproporcional: Se o prejuízo atual está em zona aceitável (ex: -0.50%, -1.20%), você só aprova a troca se houver no lote uma moeda com Confiança >= 95. Trocar um ativo ruim por um "mais ou menos" destrói capital.
3. A Lei do Cansaço: Analise o 'Tempo na Operação'. Se a moeda está presa há muitas horas (ex: >10h) e recuperou pro zero a zero ou leve prejuízo, a tese falhou por fadiga. Aprove a troca se houver boa oportunidade.

MÉTODO DE ANÁLISE OBRIGATÓRIO (CHAIN OF THOUGHT EM 3 PASSOS):
- Passo 1: Auditoria da Posição Atual (O Prejuízo Atual está na zona permitida de 0.00% a -1.50%? Qual o nível de fadiga do Tempo na Operação?).
- Passo 2: Auditoria das Candidatas (Execute a análise Macro/Micro rigorosa no lote. Existe alguma moeda com setup MATADOR de 95%+ de confiança?).
- Passo 3: O Veredito Final (Se o Passo 1 barrar a operação pelo escudo de -1.50%, ou o Passo 2 não achar moeda matadora, o veredito é HOLD).

FORMATO DE SAÍDA JSON ESPERADO (RESPONDA APENAS O JSON, SEM TEXTOS EXTRAS):
{
  "auditoria_posicao_atual": "string (Análise do Prejuízo e Tempo)",
  "auditoria_candidatas": "string (Análise rápida do lote de substituição)",
  "moeda_vencedora": "string (Símbolo da nova moeda perfeita ou 'HOLD')",
  "confianca_final": 0 a 100,
  "resumo_decisao": "string (Se vetou o swap, declare: 'HOLD mantido devido à Lei do Teto de Prejuízo' ou 'Falta de oportunidade de 95%+ no lote'. Se aprovou, justifique o setup perfeito da nova moeda.)"
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