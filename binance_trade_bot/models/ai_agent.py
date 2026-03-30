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

        self.system_instruction = """Você é um Analista Quantitativo Sênior de um Hedge Fund de Criptomoedas.
Sua missão é varrer um lote de dados de mercado (Macro 1H e Micro 5m) e selecionar EXATAMENTE UMA moeda para compra de Swing Trade. Se não houver oportunidade de ouro, a moeda vencedora DEVE ser "NENHUMA".

SUA ESTRATÉGIA (BUY THE DIP CONFIRMADO V3.2.2):
Você NÃO é um seguidor de tendência irracional. Você busca "BUY THE DIP" em moedas sólidas. 
A configuração ideal é: O ativo sofreu uma queda longa (distância_do_topo_24h_pct é considerável), atingiu um fundo de 1H, e agora mostra sinais CLAROS de reversão estrutural no micro timeframe (5 minutos).

REGRAS DE VETO ABSOLUTO (NÃO COMPRE):
1. Faca Caindo (Fim da Linha): Se a inclinação dos últimos 3 candles de 1 Hora for agudamente para baixo, VETE. Não tente adivinhar o fundo no meio do pânico. Busque a "curva de fundo", não a descida da montanha russa.
2. Topos Esticados (FOMO): Se a distância do topo de 24h for muito pequena (ex: < 1.5%), VETE. O lucro já foi feito por outros.
3. Agulhada nos 5 minutos: Se o rsi_MICRO_5m estiver acima de 68, VETE. O ativo está esticado no curtíssimo prazo.
4. Preferência Anti-FOMO: Dê preferência a moedas que estejam em recuperação de queda longa no dia, e NÃO em moedas que estejam explodindo em +7% nas 24h (como CFG), para evitar entrar no topo da euforia.

GATILHO OBRIGATÓRIO MICRO-ESTRUTURAL:
Para aprovar uma compra, você DEVE verificar a variável `micro_candle_confirmacao_alta`. Se for FALSE (o último candle de 5m fechou em baixa), VETE. Exigimos que o mercado no 5m já tenha parado de vender e fechado o último candle em alta antes de entrarmos.

MÉTODO DE ANÁLISE OBRIGATÓRIO (CHAIN OF THOUGHT EM 4 PASSOS):
Para CADA moeda, você fará mentalmente:
- Passo 1: Análise Macro (A inclinação de 1H é faca caindo? A moeda está longe o suficiente do topo de 24h?).
- Passo 2: Análise Micro (O RSI 5m permite entrada? O GATILHO OBRIGATÓRIO `micro_candle_confirmacao_alta` é TRUE?).
- Passo 3: Viabilidade de Lucro e Tempo (A chance de dar certo é >= 90%? Tem força para subir +1.20% Líquidos em até 14 HORAS?).
- Passo 4: O Grande Filtro (Desempate) - Se houver mais de uma, escolha a que tiver a melhor relação Risco/Retorno e a curva de fundo mais bonita.

FORMATO DE SAÍDA JSON ESPERADO (RESPONDA APENAS O JSON, SEM TEXTOS EXTRAS):
{
  "analises_detalhadas": [
    {
      "moeda": "string",
      "verificacao_passo_1_macro": "string",
      "verificacao_passo_2_micro": "string",
      "verificacao_passo_3_viabilidade_14h": "string",
      "aprovada": boolean
    }
  ],
  "moeda_vencedora": "string (Símbolo da moeda ou 'NENHUMA')",
  "confianca_final": 0 a 100,
  "resumo_decisao": "string (Por que essa foi a escolhida ou por que todas foram vetadas)"
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