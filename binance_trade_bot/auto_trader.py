from datetime import datetime
from typing import Dict, List
import time
import os

from sqlalchemy.orm import Session

from .binance_api_manager import BinanceAPIManager
from .config import Config
from .database import Database
from .logger import Logger
from .models import Coin, CoinValue, Pair


class AutoTrader:
    def __init__(
        self,
        binance_manager: BinanceAPIManager,
        database: Database,
        logger: Logger,
        config: Config,
    ):
        self.manager = binance_manager
        self.db = database
        self.logger = logger
        self.config = config
        self.cooldowns = {} 
        
        self.cooldown_minutos = 60
        self.min_24h_change = 2.0 # REGRA DE OURO
        try:
            if os.path.exists('user.cfg'):
                with open('user.cfg', 'r') as f:
                    for linha in f:
                        linha = linha.strip()
                        if linha.startswith('cooldown_minutos'): self.cooldown_minutos = int(linha.split('=')[1].strip())
                        elif linha.startswith('min_24h_change'): self.min_24h_change = float(linha.split('=')[1].strip())
        except: pass

    def initialize(self):
        self.auto_detect_current_coin()
        self.initialize_trade_thresholds()
    
    def auto_detect_current_coin(self):
        self.logger.info("[?] Analisando a carteira na Binance para sincronizar o bot...")
        best_coin = None
        max_usd_value = 0

        for coin in self.db.get_coins():
            balance = self.manager.get_currency_balance(coin.symbol, force=True)
            if balance <= 0: continue
            price = self.manager.get_ticker_price(coin + self.config.BRIDGE)
            if price is None: continue
            usd_value = balance * price

            if usd_value > 5 and usd_value > max_usd_value:
                max_usd_value = usd_value
                best_coin = coin

        if best_coin:
            self.logger.info(f"[OK] Auto-detect: Encontrei {best_coin.symbol} valendo ${max_usd_value:.2f}. Assumindo o controle dela!")
            self.db.set_current_coin(best_coin)
            self.update_trade_threshold(best_coin, self.manager.get_ticker_price(best_coin + self.config.BRIDGE))
        else:
            bridge_balance = self.manager.get_currency_balance(self.config.BRIDGE.symbol, force=True)
            self.logger.info(f"[OK] Auto-detect: Nenhuma altcoin > $5 encontrada. Dinheiro livre em {self.config.BRIDGE.symbol}: ${bridge_balance:.2f}")
            from .models import CurrentCoin
            with self.db.db_session() as session: session.query(CurrentCoin).delete()

    def transaction_through_bridge(self, pair: Pair):
        balance = self.manager.get_currency_balance(pair.from_coin.symbol, force=True)
        from_coin_price = self.manager.get_ticker_price(pair.from_coin + self.config.BRIDGE)

        if from_coin_price is None:
            self.logger.info("Skipping sell (API atrasada, preço não encontrado)")
            return None

        min_notional = self.manager.get_min_notional(pair.from_coin.symbol, self.config.BRIDGE.symbol)

        if balance and (balance * from_coin_price > min_notional):
            if self.manager.sell_alt(pair.from_coin, self.config.BRIDGE) is None:
                self.logger.info("Couldn't sell, going back to scouting mode...")
                return None
            else:
                self.cooldowns[pair.from_coin.symbol] = time.time() + (self.cooldown_minutos * 60)
        else:
            self.logger.warning(f"Abortando JUMP! Saldo de {pair.from_coin.symbol} insuficiente.")
            return None

        result = self.manager.buy_alt(pair.to_coin, self.config.BRIDGE)
        if result is not None:
            self.db.set_current_coin(pair.to_coin)
            self.update_trade_threshold(pair.to_coin, result.price)
            return result

        self.logger.info("Couldn't buy, going back to scouting mode...")
        return None

    def update_trade_threshold(self, coin: Coin, coin_price: float):
        if coin_price is None: return
        session: Session
        with self.db.db_session() as session:
            for pair in session.query(Pair).filter(Pair.to_coin == coin):
                from_coin_price = self.manager.get_ticker_price(pair.from_coin + self.config.BRIDGE)
                if from_coin_price is None: continue
                pair.ratio = from_coin_price / coin_price

    def initialize_trade_thresholds(self):
        session: Session
        with self.db.db_session() as session:
            for pair in session.query(Pair).filter(Pair.ratio.is_(None)).all():
                if not pair.from_coin.enabled or not pair.to_coin.enabled: continue
                self.logger.info(f"Initializing {pair.from_coin} vs {pair.to_coin}")
                from_coin_price = self.manager.get_ticker_price(pair.from_coin + self.config.BRIDGE)
                if from_coin_price is None: continue
                to_coin_price = self.manager.get_ticker_price(pair.to_coin + self.config.BRIDGE)
                if to_coin_price is None: continue
                pair.ratio = from_coin_price / to_coin_price

    def scout(self):
        raise NotImplementedError()

    def _get_ratios(self, coin: Coin, coin_price):
        ratio_dict: Dict[Pair, float] = {}
        
        # Puxa o status das 24h de todas as moedas de uma vez
        all_24h = self.manager.get_all_tickers_24h()

        for pair in self.db.get_pairs_from(coin):
            if pair.to_coin.symbol in self.cooldowns:
                if time.time() < self.cooldowns[pair.to_coin.symbol]: continue 
                else: del self.cooldowns[pair.to_coin.symbol]

            # --- REGRA DE OURO (MOMENTUM) ---
            symbol_str = pair.to_coin.symbol + self.config.BRIDGE.symbol
            coin_change = all_24h.get(symbol_str, -999.0)
            if coin_change < self.min_24h_change:
                continue # Ignora a matemática se a tendência da moeda nova for fraca
            # --------------------------------

            optional_coin_price = self.manager.get_ticker_price(pair.to_coin + self.config.BRIDGE)
            if optional_coin_price is None: continue

            self.db.log_scout(pair, pair.ratio, coin_price, optional_coin_price)
            coin_opt_coin_ratio = coin_price / optional_coin_price
            from_fee = self.manager.get_fee(pair.from_coin, self.config.BRIDGE, True)
            to_fee = self.manager.get_fee(pair.to_coin, self.config.BRIDGE, False)
            transaction_fee = from_fee + to_fee - from_fee * to_fee

            if self.config.USE_MARGIN == "yes":
                ratio_dict[pair] = ((1 - transaction_fee) * coin_opt_coin_ratio / pair.ratio - 1 - self.config.SCOUT_MARGIN / 100)
            else:
                ratio_dict[pair] = (coin_opt_coin_ratio - transaction_fee * self.config.SCOUT_MULTIPLIER * coin_opt_coin_ratio) - pair.ratio
        return ratio_dict

    def _jump_to_best_coin(self, coin: Coin, coin_price: float):
        ratio_dict = self._get_ratios(coin, coin_price)
        ratio_dict = {k: v for k, v in ratio_dict.items() if v > 0}

        if ratio_dict:
            best_pair = max(ratio_dict, key=ratio_dict.get)
            self.logger.info(f"Will be jumping from [{coin}] to {best_pair.to_coin_id}")
            self.transaction_through_bridge(best_pair)

    def bridge_scout(self):
        bridge_balance = self.manager.get_currency_balance(self.config.BRIDGE.symbol, force=True)
        all_24h = self.manager.get_all_tickers_24h()

        for coin in self.db.get_coins():
            if coin.symbol in self.cooldowns:
                if time.time() < self.cooldowns[coin.symbol]: continue 
                else: del self.cooldowns[coin.symbol]

            # --- REGRA DE OURO (MOMENTUM) ---
            symbol_str = coin.symbol + self.config.BRIDGE.symbol
            coin_change = all_24h.get(symbol_str, -999.0)
            if coin_change < self.min_24h_change:
                continue # Não sai do Dólar para comprar moeda fraca
            # --------------------------------

            current_coin_price = self.manager.get_ticker_price(coin + self.config.BRIDGE)
            if current_coin_price is None: continue

            ratio_dict = self._get_ratios(coin, current_coin_price)
            if not any(v > 0 for v in ratio_dict.values()):
                if bridge_balance > self.manager.get_min_notional(coin.symbol, self.config.BRIDGE.symbol):
                    self.logger.info(f"Will be purchasing [{coin}] using bridge coin")
                    self.manager.buy_alt(coin, self.config.BRIDGE)
                    return coin
        return None

    def update_values(self):
        now = datetime.now()
        session: Session
        with self.db.db_session() as session:
            coins: List[Coin] = session.query(Coin).all()
            for coin in coins:
                balance = self.manager.get_currency_balance(coin.symbol)
                if balance == 0: continue
                usd_value = self.manager.get_ticker_price(coin + "USDT")
                btc_value = self.manager.get_ticker_price(coin + "BTC")
                cv = CoinValue(coin, balance, usd_value, btc_value, datetime=now)
                session.add(cv)
                self.db.send_update(cv)
                