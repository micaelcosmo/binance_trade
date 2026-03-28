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
            # NOVO SDK OFICIAL DO GOOGLE (Adeus LangChain e Warnings!)
            self.client = genai.Client(api_key=google_api_key)

        self.system_instruction = """Você é um Gestor de Portfólio Institucional e Analista Quantitativo Sênior.
Sua função é receber um lote de dados técnicos pré-processados de MÚLTIPLAS criptomoedas e identificar a ÚNICA melhor oportunidade de Swing Trade. O objetivo é buscar um lucro seguro de pelo menos +2.00%.

O SEU FLUXO DE TRABALHO OBRIGATÓRIO É (Chain of Thought):
1º Passo: Analise os indicadores pré-calculados (RSI, EMAs, Volume e Variações) de CADA moeda individualmente.
2º Passo: Compare as moedas entre si, avaliando qual tem a melhor estrutura de alta e relação risco/retorno.
3º Passo: Escolha a melhor oportunidade ou, se o mercado estiver ruim, fique de fora.

REGRAS DE VETO ABSOLUTO (NÃO COMPRE SE):
- Filtro Anti-Faca Caindo: VETE sumariamente moedas com preço abaixo das EMAs principais, com tendência de volume de venda ou próximas da mínima das últimas 24h. Não tente adivinhar o fundo do poço.
- Filtro Anti-FOMO (Fear Of Missing Out): VETE sumariamente moedas com RSI estourado (ex: acima de 70) ou que já estão coladas na máxima das últimas 24h. Se o lucro de 2% já foi precificado, descarte a moeda.

Regras estritas:
1. Baseie-se APENAS na matemática e nos dados fornecidos.
2. Seja extremamente frio e institucional. Se todas as moedas caírem nos "Vetores Absolutos" ou não apresentarem um setup claríssimo, a moeda vencedora DEVE ser "NENHUMA".
3. A sua resposta SERÁ PARSEADA POR UM SISTEMA. Retorne APENAS o JSON válido, sem markdown ou explicações externas.

FORMATO DE SAÍDA JSON ESPERADO:
{
  "analises_individuais": [
    {
      "moeda": "string",
      "leitura_tecnica": "string",
      "potencial_alta": "string (BAIXO, MEDIO, ALTO)"
    }
  ],
  "resumo_comparativo": "string",
  "moeda_vencedora": "string (Símbolo da moeda ou 'NENHUMA')",
  "confianca_setup": 0,
  "motivo_investimento": "string",
  "alertas_risco": "string"
}"""

    def analisar_lote(self, lote_dados):
        if not self.client:
            return {"moeda_vencedora": "COMPRA_TESTE", "confianca_setup": 100, "motivo_investimento": "Modo Bypass (Sem API Key configurada)"}

        try:
            lote_json_string = json.dumps(lote_dados, indent=2)
            prompt_texto = f"Por favor, analise o lote de dados quantitativos abaixo, compare os ativos e retorne a sua decisão final de alocação em formato JSON puro.\n\nLOTE DE DADOS DE HOJE:\n{lote_json_string}"
            
            # Usando o Flash-Lite para ter acesso a mais de 1000 requisições diárias no Free Tier
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

            # Auditoria de Tokens via novo SDK
            usage = response.usage_metadata
            if usage:
                tokens_in = getattr(usage, 'prompt_token_count', 0)
                tokens_out = getattr(usage, 'candidates_token_count', 0)
                total_tokens = getattr(usage, 'total_token_count', 0)
                self.system_logger.info(f"📊 [API AUDIT] Tokens consumidos neste lote -> Input: {tokens_in} | Output: {tokens_out} | Total: {total_tokens}")
            
            resposta_bruta = response.text

            # Limpeza cirúrgica
            resposta_limpa = resposta_bruta.strip('`').replace('json\n', '').strip()
            resposta_json = json.loads(resposta_limpa)
            
            return resposta_json

        except Exception as erro_execucao:
            self.system_logger.error(f"Erro Crítico no Parser JSON/API da IA: {erro_execucao}")
            return {"moeda_vencedora": "NENHUMA", "confianca_setup": 0, "motivo_investimento": "Falha na comunicação ou conversão da resposta da IA."}