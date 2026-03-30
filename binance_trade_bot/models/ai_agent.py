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

SUA ESTRATÉGIA (HORIZONTE DE 24 HORAS):
Seu horizonte de investimento NÃO é de curtíssimo prazo (minutos/poucas horas). Você busca lucros no fechamento do dia (Swing Trade de 24 horas). 
A configuração ideal é "BUY THE DIP" em moedas sólidas. O ativo deve ter sofrido uma queda longa no dia, atingido um fundo estrutural no gráfico Macro (1H) e confirmado reversão no Micro (5m).

REGRAS DE VETO ABSOLUTO (NÃO COMPRE):
1. Faca Caindo: Se a inclinação dos últimos 3 candles de 1 Hora for agudamente para baixo, VETE. Busque a "curva de fundo", não a queda vertical.
2. Topos Esticados: Se a distância do topo de 24h for muito pequena (ex: < 1.5%), VETE.
3. Agulhada nos 5 minutos: Se o rsi_MICRO_5m estiver acima de 68, VETE.
4. Anti-FOMO: Evite moedas que já explodiram +7% ou mais no dia de hoje.

GATILHO OBRIGATÓRIO MICRO-ESTRUTURAL:
A variável `micro_candle_confirmacao_alta` DEVE ser TRUE. Se for FALSE (o último candle de 5m fechou em baixa), VETE a moeda.

MÉTODO DE ANÁLISE OBRIGATÓRIO (CHAIN OF THOUGHT EM 4 PASSOS):
- Passo 1: Análise Macro (É faca caindo? A moeda está longe o suficiente do topo de 24h?).
- Passo 2: Análise Micro (O RSI 5m permite entrada? O GATILHO micro_candle_confirmacao_alta é TRUE?).
- Passo 3: Viabilidade (Tem força para subir +1.20 a +2.00% Líquidos ao longo do dia inteiro, sem bater em resistências pesadas?).
- Passo 4: Desempate (A que tiver a melhor relação Risco/Retorno ao longo das próximas 24h).

FORMATO DE SAÍDA JSON ESPERADO (RESPONDA APENAS O JSON):
{
  "analises_detalhadas": [
    {
      "moeda": "string",
      "verificacao_passo_1_macro": "string",
      "verificacao_passo_2_micro": "string",
      "verificacao_passo_3_viabilidade_24h": "string",
      "aprovada": boolean
    }
  ],
  "moeda_vencedora": "string (Símbolo ou 'NENHUMA')",
  "confianca_final": 0 a 100,
  "resumo_decisao": "string"
}"""

        self.system_instruction_swap = """Você é o Tribunal de Auditoria de Swap (Hedge Fund Institucional).
O operador está PRESO em uma operação, segurando uma moeda ('moeda_atual') e acumulando prejuízo ('prejuizo_atual_pct').
O horizonte de investimento é de 24 HORAS. O robô tem plena paciência matemática para aguardar a recuperação do ativo atual ao longo de todo o dia.

SUA MISSÃO:
Julgar se o robô deve fazer "HOLD" (ter paciência, segurar o prejuízo temporário e aguardar o ativo recuperar) ou aprovar um "SWAP DE EMERGÊNCIA" (vender assumindo o prejuízo agora e trocar para uma nova moeda do lote).

A REGRA DE OURO (O GRANDE FILTRO):
Você SÓ PODE aprovar o swap se encontrar no lote de dados uma nova moeda com configuração PERFEITA e MATADORA (Certeza Absoluta, confianca_final >= 95).
A nova moeda deve ter uma probabilidade esmagadora (>= 95%) de explodir nas próximas horas, garantindo não só a recuperação do prejuízo da moeda antiga, como a geração de lucro líquido.
Se nenhuma moeda do lote for uma oportunidade óbvia de 95%+, a sua decisão DEVE OBRIGATORIAMENTE ser "HOLD". Não troque seis por meia dúzia. O mercado pune os impacientes. Deixe a moeda atual recuperar.

FORMATO DE SAÍDA JSON ESPERADO (RESPONDA APENAS O JSON, SEM TEXTOS EXTRAS):
{
  "moeda_vencedora": "string (Símbolo da nova moeda perfeita ou 'HOLD')",
  "confianca_final": 0 a 100,
  "resumo_decisao": "string (Justificativa detalhada do porquê aprovou o Swap com 95%+ de certeza, ou por que preferiu manter o HOLD por prudência e paciência no mercado)"
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

    def analisar_swap(self, lote_dados, moeda_atual, prejuizo_atual):
        if not self.client:
            return {"moeda_vencedora": "HOLD", "confianca_final": 0, "resumo_decisao": "Modo Bypass (Sem API Key)"}

        try:
            lote_json_string = json.dumps(lote_dados, indent=2)
            prompt_texto = f"SITUAÇÃO DO OPERADOR:\n- Moeda Atual em Carteira: {moeda_atual}\n- Prejuízo Atual: {prejuizo_atual:.2f}%\n\nLOTE DE DADOS DISPONÍVEIS PARA SWAP:\n{lote_json_string}\n\nJulgue com extrema severidade e retorne a decisão em JSON."
            
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