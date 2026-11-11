"""Exchange mock (spot, só ordens market) para simulação e testes.

- Saldo em USDT (quote) + saldos por ativo.
- Ordens market com taxa (padrão 0,1% — taxa spot Binance sem BNB) e
  slippage configurável em fração (0,0005 = 0,05%), sempre CONTRA o usuário:
  compra executa acima do preço de referência, venda abaixo.
- Taxa cobrada no ativo recebido (como a Binance faz sem desconto BNB):
  compra → taxa em moeda base; venda → taxa em USDT.
- Histórico de fills com preço executado real (``Fill.price``).

Interface mínima e independente da python-binance de propósito: o motor de
simulação chama ``market_buy_quote`` / ``market_sell_qty`` diretamente. Uma
fachada compatível com ``binance_client`` pode ser construída por cima depois.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class InsufficientBalance(Exception):
    pass


@dataclass
class Fill:
    ts: int            # timestamp (ms) da execução
    symbol: str        # ex.: "BTCUSDT"
    side: str          # "BUY" | "SELL"
    ref_price: float   # preço de referência (ex.: open da vela seguinte)
    price: float       # preço executado (com slippage)
    qty: float         # quantidade da moeda base negociada (bruta)
    quote: float       # USDT movimentado (bruto, antes da taxa quando venda)
    fee: float         # taxa cobrada
    fee_asset: str
    reason: str = ""


@dataclass
class MockExchange:
    quote_asset: str = "USDT"
    fee_rate: float = 0.001
    slippage: float = 0.0005
    min_notional: float = 5.0
    balances: dict = field(default_factory=dict)
    fills: list = field(default_factory=list)

    @classmethod
    def with_balance(cls, usdt: float = 1000.0, **kw) -> "MockExchange":
        ex = cls(**kw)
        ex.balances[ex.quote_asset] = float(usdt)
        return ex

    # ------------------------------------------------------------------ util
    def balance(self, asset: str) -> float:
        return self.balances.get(asset, 0.0)

    def _base(self, symbol: str) -> str:
        if not symbol.endswith(self.quote_asset):
            raise ValueError(f"símbolo {symbol} não é par {self.quote_asset}")
        return symbol[: -len(self.quote_asset)]

    def equity(self, prices: dict) -> float:
        """Valor total em quote, marcando cada ativo a ``prices[asset]``."""
        total = self.balance(self.quote_asset)
        for asset, qty in self.balances.items():
            if asset != self.quote_asset and qty:
                total += qty * prices.get(asset, 0.0)
        return total

    # ---------------------------------------------------------------- ordens
    def market_buy_quote(self, symbol: str, quote_qty: float, ref_price: float, ts: int = 0,
                         reason: str = "") -> Fill:
        """Compra gastando ``quote_qty`` USDT (equivale a quoteOrderQty)."""
        if ref_price <= 0:
            raise ValueError("preço de referência inválido")
        quote_qty = float(quote_qty)
        if quote_qty < self.min_notional:
            raise InsufficientBalance(f"notional {quote_qty:.2f} < mínimo {self.min_notional}")
        if quote_qty > self.balance(self.quote_asset) + 1e-9:
            raise InsufficientBalance("saldo USDT insuficiente")
        base = self._base(symbol)
        price = ref_price * (1.0 + self.slippage)
        gross_qty = quote_qty / price
        fee = gross_qty * self.fee_rate
        self.balances[self.quote_asset] = self.balance(self.quote_asset) - quote_qty
        self.balances[base] = self.balance(base) + gross_qty - fee
        fill = Fill(ts, symbol, "BUY", ref_price, price, gross_qty, quote_qty, fee, base, reason)
        self.fills.append(fill)
        return fill

    def limit_buy_quote(self, symbol: str, quote_qty: float, limit_price: float, ts: int = 0,
                        reason: str = "") -> Fill:
        """Compra limit (maker) JÁ EXECUTADA ao preço limite: sem slippage.

        Quem decide SE a ordem executou é o chamador (o motor exige que a
        mínima atravesse o limite — regra conservadora)."""
        slip, self.slippage = self.slippage, 0.0
        try:
            fill = self.market_buy_quote(symbol, quote_qty, limit_price, ts, reason)
        finally:
            self.slippage = slip
        return fill

    def market_sell_qty(self, symbol: str, qty: float, ref_price: float, ts: int = 0,
                        reason: str = "") -> Fill:
        """Vende ``qty`` da moeda base a mercado."""
        if ref_price <= 0:
            raise ValueError("preço de referência inválido")
        base = self._base(symbol)
        qty = float(qty)
        if qty > self.balance(base) + 1e-12:
            raise InsufficientBalance(f"saldo {base} insuficiente")
        price = ref_price * (1.0 - self.slippage)
        gross_quote = qty * price
        if gross_quote < self.min_notional:
            raise InsufficientBalance(f"notional {gross_quote:.2f} < mínimo {self.min_notional}")
        fee = gross_quote * self.fee_rate
        self.balances[base] = self.balance(base) - qty
        self.balances[self.quote_asset] = self.balance(self.quote_asset) + gross_quote - fee
        fill = Fill(ts, symbol, "SELL", ref_price, price, qty, gross_quote, fee, self.quote_asset, reason)
        self.fills.append(fill)
        return fill

    def sell_all(self, symbol: str, ref_price: float, ts: int = 0, reason: str = "") -> Fill:
        return self.market_sell_qty(symbol, self.balance(self._base(symbol)), ref_price, ts, reason)

    def buy_all_in(self, symbol: str, ref_price: float, ts: int = 0, fraction: float = 0.99,
                   reason: str = "") -> Fill:
        """Replica a entrada da profit_gain: 99% do saldo livre em USDT."""
        return self.market_buy_quote(symbol, self.balance(self.quote_asset) * fraction, ref_price, ts, reason)


def round_trip_multiplier(fee_rate: float, slippage: float) -> float:
    """Fator líquido de um round-trip market (compra+venda) com preço constante."""
    return (1 - fee_rate) ** 2 * (1 - slippage) / (1 + slippage)
