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
            self.system_logger.warning("⚠️ GOOGLE_API_KEY não encontrada no user.cfg! O Agente IA vai rodar em modo 'cego' (Bypass automático).")
            self.client = None
        else:
            self.client = genai.Client(api_key=google_api_key)

        # O NOVO CÉREBRO: Regra dos 90%, 3 Passos e "Buy the Dip"
        self.system_instruction = """Você é um Analista Quantitativo Sênior de um Hedge Fund de Criptomoedas.
Sua missão é varrer um lote de dados de mercado (Macro 1H e Micro 5m) e selecionar EXATAMENTE UMA moeda para compra de Swing Trade, exigindo 90% DE CONFIANÇA ou mais. Se não houver oportunidade de ouro, a moeda vencedora DEVE ser "NENHUMA".

SUA ESTRATÉGIA (O QUE VOCÊ BUSCA):
Você NÃO é um seguidor de tendência irracional. Você busca "BUY THE DIP" em moedas sólidas. 
A configuração ideal é: O ativo sofreu uma queda longa (distância_do_topo_24h_pct é considerável, ex: > 4%), mas atingiu um fundo, consolidou e agora os indicadores começaram a virar para alta (RSI 1H subindo de baixo, preço cruzando a EMA). 

REGRAS DE VETO ABSOLUTO (NÃO COMPRE):
1. Topos Esticados (Montanha Russa): Se a distância do topo de 24h for muito pequena (ex: < 1.5%), VETE. O lucro já foi feito por outras pessoas.
2. Agulhada nos 5 minutos: Se o rsi_MICRO_5m estiver acima de 68, VETE. O ativo está esticado no curtíssimo prazo e vai corrigir na nossa cara logo após a compra.
3. Queda Livre sem Suporte: Se a moeda estiver sangrando sem parar e o RSI 1H estiver mergulhando para baixo de 40 sem sinal de repique, VETE.

MÉTODO DE ANÁLISE OBRIGATÓRIO (CHAIN OF THOUGHT EM 3 PASSOS):
Para CADA moeda, você fará mentalmente:
- Passo 1: Análise Macro (A moeda tem potencial de reverter uma queda ou está muito perto do topo de 24h?).
- Passo 2: Análise Micro (O rsi_MICRO_5m permite uma entrada segura agora, ou vou comprar um topo de 5 minutos?).
- Passo 3: Advogado do Diabo (Quais são as chances de dar errado? Tem espaço para bater os +2% de lucro sem sofrer resistência pesada?).

FORMATO DE SAÍDA JSON ESPERADO (RESPONDA APENAS O JSON, SEM TEXTOS EXTRAS):
{
  "analises_detalhadas": [
    {
      "moeda": "string",
      "verificacao_passo_1_macro": "string",
      "verificacao_passo_2_micro": "string",
      "verificacao_passo_3_risco": "string",
      "aprovada": boolean
    }
  ],
  "moeda_vencedora": "string (Símbolo da moeda ou 'NENHUMA')",
  "confianca_final": 0 a 100,
  "resumo_decisao": "string (Por que essa foi a escolhida ou por que tudo foi vetado)"
}"""

    def analisar_lote(self, lote_dados):
        if not self.client:
            return {"moeda_vencedora": "COMPRA_TESTE", "confianca_final": 100, "resumo_decisao": "Modo Bypass (Sem API Key configurada)"}

        try:
            lote_json_string = json.dumps(lote_dados, indent=2)
            prompt_texto = f"Por favor, execute a Análise em 3 Passos rigorosa no lote de dados abaixo e retorne a sua decisão final em JSON.\n\nLOTE DE DADOS DE HOJE:\n{lote_json_string}"
            
            response = self.client.models.generate_content(
                model='gemini-2.5-flash-lite',
                contents=prompt_texto,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
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
                self.system_logger.info(f"📊 [API AUDIT] Tokens consumidos neste lote -> Input: {tokens_in} | Output: {tokens_out} | Total: {total_tokens}")
            
            resposta_bruta = response.text

            resposta_limpa = resposta_bruta.strip('`').replace('json\n', '').strip()
            resposta_json = json.loads(resposta_limpa)
            
            return resposta_json

        except Exception as erro_execucao:
            self.system_logger.error(f"Erro Crítico no Parser JSON/API da IA: {erro_execucao}")
            return {"moeda_vencedora": "NENHUMA", "confianca_final": 0, "resumo_decisao": "Falha na comunicação ou conversão da resposta da IA."}