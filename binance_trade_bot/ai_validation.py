"""
Validação/normalização da saída da IA (spec 002 / issue AI-01).

A IA (Gemini) é um conselheiro NÃO-confiável cuja saída entra num caminho que
move capital real. Nenhum campo pode ser usado sem validação. Filosofia
fail-closed: qualquer anomalia vira um veto seguro (NENHUMA/HOLD/ERROR_503 com
confidence=0). O pior caso é "perdeu uma entrada", nunca "entrou errado".

Função pura e sem dependências externas => trivial de testar isolada.
"""

# Sentinelas canônicas de veto/erro.
SENTINEL_NONE = "NENHUMA"     # nenhuma candidata aprovada (analyze_batch)
SENTINEL_HOLD = "HOLD"        # manter posição atual (analyze_swap)
SENTINEL_ERROR = "ERROR_503"  # falha de comunicação/parse/validação

_VETO_SENTINELS = {SENTINEL_NONE, SENTINEL_HOLD, SENTINEL_ERROR}

# Sufixos de par comuns; usados para normalizar tickers "sujos" (ex.: BTCUSDT -> BTC).
_KNOWN_BRIDGES = ("USDT", "FDUSD", "BUSD", "USDC", "TUSD", "USD", "BTC")

_DEFAULT_SUMMARY = "Sem parecer fornecido pela IA."
_MAX_SUMMARY_LEN = 4000


def _coerce_confidence(raw_value):
    """Converte confiança para int em [0, 100]; qualquer coisa inválida -> 0."""
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return 0
    if value != value or value in (float("inf"), float("-inf")):  # NaN/inf
        return 0
    return int(max(0, min(100, round(value))))


def _normalize_ticker(raw_value, batch_coins):
    """
    Normaliza `winning_coin`. Retorna (ticker_ou_sentinela, foi_alucinacao).
    - sentinelas de veto são preservadas na forma canônica;
    - tickers válidos precisam existir no batch (direto ou após remover o par);
    - ticker inexistente no batch -> alucinação (o chamador rebaixa para veto).
    """
    candidate = str(raw_value).strip().upper()

    for sentinel in _VETO_SENTINELS:
        if candidate == sentinel:
            return sentinel, False

    if candidate in batch_coins:
        return candidate, False

    # Tenta remover um sufixo de par (BTCUSDT -> BTC) e casar com o batch.
    for bridge in _KNOWN_BRIDGES:
        if candidate.endswith(bridge) and len(candidate) > len(bridge):
            stripped = candidate[: -len(bridge)]
            if stripped in batch_coins:
                return stripped, False

    return candidate, True  # não existe no batch => alucinação


def normalize_verdict(raw, batch_coins, mode="batch", audit=None):
    """
    Normaliza a saída crua da IA para o contrato garantido:
        { winning_coin: str, final_confidence: int[0..100], decision_summary: str }

    Args:
        raw: objeto retornado por json.loads (dict esperado; qualquer coisa é tolerada).
        batch_coins: iterável de tickers submetidos (serão normalizados p/ UPPER).
        mode: 'batch' (veto = NENHUMA) ou 'swap' (veto = HOLD).
        audit: callable(str) opcional para registrar correções aplicadas.
    """
    veto_coin = SENTINEL_HOLD if mode == "swap" else SENTINEL_NONE
    coins = {str(c).strip().upper() for c in (batch_coins or [])}

    def _note(message):
        if audit:
            try:
                audit(message)
            except Exception:
                pass

    def _safe_veto(reason, coin=None):
        _note(reason)
        return {
            "winning_coin": coin or veto_coin,
            "final_confidence": 0,
            "decision_summary": "Saída da IA inválida; veto por segurança."
            if coin == SENTINEL_ERROR
            else _DEFAULT_SUMMARY,
        }

    # step_0: precisa ser dict.
    if not isinstance(raw, dict):
        return _safe_veto("verdict_nao_dict", coin=SENTINEL_ERROR)

    # step_1: winning_coin.
    ticker, hallucinated = _normalize_ticker(raw.get("winning_coin", veto_coin), coins)
    if hallucinated:
        _note(f"alucinacao_de_ticker:{ticker}")
        ticker = veto_coin

    # step_2: confidence.
    confidence = _coerce_confidence(raw.get("final_confidence", 0))

    # step_3: summary.
    summary = raw.get("decision_summary")
    if not isinstance(summary, str) or not summary.strip():
        summary = _DEFAULT_SUMMARY
        _note("summary_ausente")
    summary = summary[:_MAX_SUMMARY_LEN]

    # step_4: consistência — sentinela de veto nunca carrega confiança positiva.
    if ticker in _VETO_SENTINELS and confidence != 0:
        _note("confidence_zerado_por_veto")
        confidence = 0

    return {
        "winning_coin": ticker,
        "final_confidence": confidence,
        "decision_summary": summary,
    }
