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

        self.system_instruction_normal = """Você é um Analista Quantitativo Sênior de um Hedge Fund de Criptomoedas.
Sua missão é varrer um lote de dados e selecionar EXATAMENTE UMA moeda para compra. Se não houver oportunidade, a moeda vencedora DEVE ser "NENHUMA".

SUA ESTRATÉGIA (A VIRADA DO NEGATIVO PROFUNDO):
Seu horizonte de investimento é o fechamento diário (Swing Trade). Você busca capturar moedas que terminaram de sangrar e estão iniciando a subida.
A configuração OBRIGATÓRIA é: O ativo tem que ter atingido uma queda profunda (obrigatoriamente ter ido abaixo de -3.00% no seu pior momento recente) e AGORA estar em fase clara de recuperação, com o micro de 5m confirmando a reversão de alta.

REGRAS DE VETO ABSOLUTO (NÃO COMPRE):
1. Faca Caindo: Se a inclinação de 1 Hora for agudamente para baixo, VETE. Busque a curva de fundo consolidada.
2. Queda Insuficiente: Se a análise não demonstrar que a moeda foi abaixo de -3.00% antes de iniciar a recuperação atual, VETE. Não queremos correções rasas.
3. Fora da Zona de Virada: VETE qualquer moeda cuja `variacao_24h_pct` atual seja MAIOR que +1.00% (o lucro já foi feito) ou MENOR que -4.00% (ainda está sangrando muito e não confirmou a virada estrutural).
4. Agulhada nos 5 minutos: Se o rsi_MICRO_5m estiver acima de 68, VETE.
5. Confirmação Micro: A variável `micro_candle_confirmacao_alta` DEVE ser TRUE. Se for FALSE, VETE.

MÉTODO DE ANÁLISE OBRIGATÓRIO (CHAIN OF THOUGHT EM 4 PASSOS):
- Passo 1: Análise de Projeção Diária (A moeda comprova que afundou além de -3% e agora está se recuperando dentro da zona de -4.00% a +1.00%?).
- Passo 2: Análise Macro (É faca caindo ou achou fundo estrutural?).
- Passo 3: Análise Micro (O RSI 5m permite entrada sem estar esticado? O GATILHO micro_candle_confirmacao_alta é TRUE?).
- Passo 4: Desempate (Escolha a moeda com o melhor setup de 'Virada do Negativo' para as próximas 24h).

FORMATO DE SAÍDA JSON ESPERADO (RESPONDA APENAS O JSON):
{
  "analises_detalhadas": [
    {
      "moeda": "string",
      "verificacao_passo_1_projecao": "string",
      "verificacao_passo_2_macro": "string",
      "verificacao_passo_3_micro": "string",
      "aprovada": boolean
    }
  ],
  "moeda_vencedora": "string (Símbolo ou 'NENHUMA')",
  "confianca_final": 0 a 100,
  "resumo_decisao": "string"
}"""

        self.system_instruction_swap = """Você é o Tribunal de Auditoria de Swap (Hedge Fund Institucional).
O operador está PRESO em uma operação, segurando uma moeda e acumulando um prejuízo ao longo do tempo.
O horizonte de investimento é de 24 HORAS. 

SUA MISSÃO:
Julgar se o robô deve fazer "HOLD" (ter paciência e aguardar a recuperação) ou aprovar um "SWAP DE EMERGÊNCIA" (vender assumindo o pequeno prejuízo agora e trocar para uma nova moeda do lote).

REGRAS DE VETO DO TRIBUNAL (OBRIGATÓRIAS):
1. TETO DE PREJUÍZO (O Escudo): Para realizar um Swap, o prejuízo atual NÃO PODE ser pior que -1.50%. Se o Prejuízo Atual for menor que -1.50% (ex: -1.60%, -3.00%, -5.00%), você DEVE OBRIGATORIAMENTE VETAR O SWAP e retornar "HOLD". O robô precisa esperar a moeda recuperar até a faixa permitida (-1.50% a 0.00%) antes de assumir o corte.
2. A NOVA MOEDA (O Gatilho): Estando na zona permitida de prejuízo (melhor ou igual a -1.50%), você só aprovará a troca se encontrar no lote uma nova moeda MATADORA (Confiança >= 95%).
3. FATOR TEMPO (Cansaço): Considere o 'Tempo na Operação'. Se a moeda estiver presa há mais de 10h, apenas lateralizando, e já recuperou para a zona segura (ex: -1.00%), a troca passa a ser altamente recomendada caso exista uma boa oportunidade, pois a tese original falhou.

FORMATO DE SAÍDA JSON ESPERADO (RESPONDA APENAS O JSON, SEM TEXTOS EXTRAS):
{
  "moeda_vencedora": "string (Símbolo da nova moeda perfeita ou 'HOLD')",
  "confianca_final": 0 a 100,
  "resumo_decisao": "string (Justificativa detalhada do porquê aprovou o Swap, ou por que manteve o HOLD - ex: 'HOLD forçado pois o prejuízo atual de -3% excede o teto máximo de swap de -1.50%')"
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
            return {"moeda_vencedora": "NENHUMA", "confianca_final": 0, "resumo_decisao": "Falha na comunicação."}

    def analisar_swap(self, lote_dados, moeda_atual, prejuizo_atual, tempo_preso_horas):
        if not self.client:
            return {"moeda_vencedora": "HOLD", "confianca_final": 0, "resumo_decisao": "Modo Bypass (Sem API Key)"}

        try:
            lote_json_string = json.dumps(lote_dados, indent=2)
            prompt_texto = f"SITUAÇÃO DO OPERADOR:\n- Moeda Atual em Carteira: {moeda_atual}\n- Prejuízo Atual: {prejuizo_atual:.2f}%\n- Tempo na Operação: {tempo_preso_horas:.1f} horas\n\nLOTE DE DADOS DISPONÍVEIS PARA SWAP:\n{lote_json_string}\n\nJulgue aplicando as Regras do Tribunal de Swap e retorne a decisão em JSON."
            
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