import random
import sys
import time
import json
import configparser
import os
from datetime import datetime

from binance_trade_bot.auto_trader import AutoTrader
from binance_trade_bot.models import CurrentCoin

class Strategy(AutoTrader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cached_trade_info = {}
        
        self.timeout_minutos = 120 
        self.btc_crash_limit = -2.5
        self.btc_recover_limit = -0.5
        self.min_24h_change = 2.0
        self.global_take_profit = 3.5 
        self.trailing_drop = 0.4      
        self.peak_profit_perc = 0.0   
        self.initial_global_balance = 0.0 
        self.is_market_crashing = False
        
        self.display_prev_coin = "Nenhuma"
        self.display_prev_atual = 0.0
        self.display_prev_venda = 0.0
        self.display_prev_poeira = 0.0
        self.last_tick_atual = 0.0
        self.last_tick_venda = 0.0
        self.last_tick_poeira = 0.0
        
        try:
            if os.path.exists('user.cfg'):
                with open('user.cfg', 'r') as f:
                    for linha in f:
                        linha = linha.strip()
                        if linha.startswith('jump_timeout'): self.timeout_minutos = int(linha.split('=')[1].strip())
                        elif linha.startswith('btc_crash_limit'): self.btc_crash_limit = float(linha.split('=')[1].strip())
                        elif linha.startswith('btc_recover_limit'): self.btc_recover_limit = float(linha.split('=')[1].strip())
                        elif linha.startswith('min_24h_change'): self.min_24h_change = float(linha.split('=')[1].strip())
                        elif linha.startswith('global_take_profit'): self.global_take_profit = float(linha.split('=')[1].strip())
                        elif linha.startswith('trailing_drop'): self.trailing_drop = float(linha.split('=')[1].strip())
        except: pass
            
        self.MAX_HOLD_TIME = self.timeout_minutos * 60
        self.last_coin = None
        self.last_jump_str = "Nenhum"
        self.jump_count = 0

    def initialize(self):
        super().initialize()
        self.initialize_current_coin()

    def get_btc_data(self):
        now = time.time()
        if not hasattr(self, 'cached_btc') or now - self.cached_btc['time'] > 60:
            try:
                ticker = self.manager.binance_client.get_ticker(symbol="BTCUSDT")
                self.cached_btc = {'time': now, 'price': float(ticker['lastPrice']), 'change': float(ticker['priceChangePercent'])}
            except Exception:
                if not hasattr(self, 'cached_btc'): self.cached_btc = {'time': now, 'price': 0.0, 'change': 0.0}
        return self.cached_btc['price'], self.cached_btc['change']

    def get_total_portfolio_value(self, current_coin_symbol=None, current_price=0.0):
        try:
            # CORREÇÃO 1: force=True para garantir o cálculo real do Trailing Stop
            free_usdt = self.manager.get_currency_balance(self.config.BRIDGE.symbol, force=True)
            if current_coin_symbol and current_price > 0:
                coin_bal = self.manager.get_currency_balance(current_coin_symbol, force=True)
                return free_usdt + (coin_bal * current_price)
            return free_usdt
        except: return 0.0

    def _write_json(self, status, coin, time_str, jumps, last_jump, btc_p=0.0, btc_c=0.0, rota="Analisando...", hot=[], cold=[], q_atual=0.0, q_venda=0.0, poeira=0.0, p_coin="Nenhuma", p_atual=0.0, p_venda=0.0, p_poeira=0.0, init_bal=0.0, peak=0.0, curr_profit=0.0):
        try:
            status_data = {
                "status": status, "coin": coin, "time": time_str, "jumps": jumps, "last_jump": last_jump, 
                "btc_price": btc_p, "btc_change": btc_c, "route": rota, "hot_coins": hot, "cold_coins": cold,
                "current_qty": q_atual, "sell_qty": q_venda, "dust": poeira,
                "prev_coin": p_coin, "prev_qty": p_atual, "prev_sell": p_venda, "prev_dust": p_poeira,
                "init_bal": init_bal, "peak_profit": peak, "curr_profit": curr_profit, 
                "global_tp": self.global_take_profit, "trailing_drop": self.trailing_drop
            }
            with open("bot_status.json", "w") as f: json.dump(status_data, f)
        except: pass

    def scout(self):
        btc_price, btc_change = self.get_btc_data()
        
        if btc_change <= self.btc_crash_limit and not self.is_market_crashing:
            self.logger.warning(f"🚨 MODO SOBREVIVÊNCIA: BTC Derreteu ({btc_change}%).")
            self.is_market_crashing = True
        elif btc_change >= self.btc_recover_limit and self.is_market_crashing:
            self.logger.info(f"✅ RECUPERAÇÃO: BTC Subiu ({btc_change}%). Voltando ao normal.")
            self.is_market_crashing = False
            
        route_str = "Acumulação (Em Queda)" if self.is_market_crashing else "Caçando Saltos (Saudável)"

        all_24h = self.manager.get_all_tickers_24h()
        hot_c = []
        cold_c = []
        for c in self.config.SUPPORTED_COIN_LIST:
            if c == "BTC": continue 
            sym = c + self.config.BRIDGE.symbol
            chg = all_24h.get(sym, -999.0)
            if chg >= self.min_24h_change: hot_c.append(f"{c} (+{chg:.2f}%)")
            else: cold_c.append(f"{c} ({chg:.2f}%)")

        current_coin = self.db.get_current_coin()
        
        if self.initial_global_balance <= 0.0:
            if current_coin:
                price_temp = self.manager.get_ticker_price(current_coin.symbol + self.config.BRIDGE.symbol)
                self.initial_global_balance = self.get_total_portfolio_value(current_coin.symbol, price_temp)
            else:
                self.initial_global_balance = self.get_total_portfolio_value()
            if self.initial_global_balance > 0:
                self.logger.info(f"🏦 Saldo Global Base: ${self.initial_global_balance:.2f}. Gatilho: +{self.global_take_profit}% | Recuo: -{self.trailing_drop}%")

        curr_profit = 0.0
        current_coin_price = 0.0
        if current_coin:
            symbol_str = current_coin.symbol + self.config.BRIDGE.symbol
            current_coin_price = self.manager.get_ticker_price(symbol_str) or 0.0
            
        if self.initial_global_balance > 0:
            current_total = self.get_total_portfolio_value(current_coin.symbol if current_coin else None, current_coin_price)
            curr_profit = ((current_total / self.initial_global_balance) - 1) * 100

        if current_coin is None:
            if self.is_market_crashing:
                self.logger.info(f"🛡️ Seguro em Dólar. Mercado caindo ({btc_change}%).")
                self._write_json("Mercado em Queda", "USDT", "--", self.jump_count, self.last_jump_str, btc_price, btc_change, route_str, hot_c, cold_c, 0.0, 0.0, 0.0, self.display_prev_coin, self.display_prev_atual, self.display_prev_venda, self.display_prev_poeira, self.initial_global_balance, self.peak_profit_perc, curr_profit)
                return

            self.logger.info(f"⏳ [RADAR] Analisando mercado com {self.config.BRIDGE.symbol}...")
            self._write_json("Buscando Oportunidade", "BUSCANDO...", "--", self.jump_count, self.last_jump_str, btc_price, btc_change, route_str, hot_c, cold_c, 0.0, 0.0, 0.0, self.display_prev_coin, self.display_prev_atual, self.display_prev_venda, self.display_prev_poeira, self.initial_global_balance, self.peak_profit_perc, curr_profit)
            self.bridge_scout()
            return

        # CORREÇÃO 2: force=True para o painel de Anterior/Atual ler o dado imaculado
        q_atual = self.manager.get_currency_balance(current_coin.symbol, force=True)
        q_venda = self.manager._sell_quantity(current_coin.symbol, self.config.BRIDGE.symbol, q_atual)
        poeira = q_atual - q_venda

        if self.last_coin != current_coin.symbol:
            if self.last_coin is not None:
                self.jump_count += 1
                self.last_jump_str = f"{self.last_coin} ➔ {current_coin.symbol}"
                self.display_prev_coin = self.last_coin
                self.display_prev_atual = self.last_tick_atual
                self.display_prev_venda = self.last_tick_venda
                self.display_prev_poeira = self.last_tick_poeira
            else:
                self.last_jump_str = f"{self.config.BRIDGE.symbol} ➔ {current_coin.symbol}"
                self.display_prev_coin = "USDT"
                self.display_prev_atual = 0.0
                self.display_prev_venda = 0.0
                self.display_prev_poeira = 0.0

            symbol_str = current_coin.symbol + self.config.BRIDGE.symbol
            self.cached_trade_info[symbol_str] = {'time': time.time()}
        
        self.last_coin = current_coin.symbol
        self.last_tick_atual = q_atual
        self.last_tick_venda = q_venda
        self.last_tick_poeira = poeira

        if current_coin_price == 0.0: return

        if self.initial_global_balance > 0 and self.global_take_profit > 0:
            if curr_profit >= self.global_take_profit:
                if curr_profit > self.peak_profit_perc:
                    self.peak_profit_perc = curr_profit
                    self.logger.info(f"📈 [TRAILING] Novo Pico Atingido: +{self.peak_profit_perc:.2f}% (Gatilho: {self.global_take_profit}%)")
                
                if curr_profit <= self.peak_profit_perc - self.trailing_drop:
                    self.logger.warning(f"💰 [VENDA TRAILING] Recuo detectado! Pico: {self.peak_profit_perc:.2f}% | Queda: -{self.trailing_drop}%.")
                    self.logger.warning(f"Vendendo {current_coin.symbol} para garantir lucro final de +{curr_profit:.2f}% em USDT!")
                    
                    if self.manager.sell_alt(current_coin, self.config.BRIDGE):
                        self.last_coin = None
                        self._reset_state_to_bridge(symbol_str, current_coin.symbol)
                        self.initial_global_balance = self.get_total_portfolio_value()
                        self.peak_profit_perc = 0.0
                        self.logger.info(f"🏦 NOVO Saldo Global (Compound): ${self.initial_global_balance:.2f}. Voltando ao Radar...")
                    return

        if symbol_str not in self.cached_trade_info:
            trades = self.manager.binance_client.get_my_trades(symbol=symbol_str, limit=5)
            buy_trades = [t for t in trades if t['isBuyer']]
            if buy_trades: self.cached_trade_info[symbol_str] = {'time': int(buy_trades[-1]['time']) / 1000.0}
            else: self.cached_trade_info[symbol_str] = {'time': time.time()}

        buy_time = self.cached_trade_info[symbol_str]['time']
        time_held = time.time() - buy_time
        mins_held = int(time_held // 60)

        if self.is_market_crashing:
            time_str = f"{mins_held}m/PAUSADO"
            self.logger.info(f"🚨 [CRASH MODE] Segurando {current_coin.symbol} | Tempo: {time_str} | Timeout cancelado.")
            self._write_json(f"Crash Mode ({btc_change}%)", current_coin.symbol, time_str, self.jump_count, self.last_jump_str, btc_price, btc_change, route_str, hot_c, cold_c, q_atual, q_venda, poeira, self.display_prev_coin, self.display_prev_atual, self.display_prev_venda, self.display_prev_poeira, self.initial_global_balance, self.peak_profit_perc, curr_profit)
        else:
            time_str = f"{mins_held}m/{self.timeout_minutos}m"
            self.logger.info(f"⏳ [JUMP RADAR] Segurando {current_coin.symbol} | Tempo: {time_str} | Calculando saltos...")
            self._write_json(f"Segurando ({time_str})", current_coin.symbol, time_str, self.jump_count, self.last_jump_str, btc_price, btc_change, route_str, hot_c, cold_c, q_atual, q_venda, poeira, self.display_prev_coin, self.display_prev_atual, self.display_prev_venda, self.display_prev_poeira, self.initial_global_balance, self.peak_profit_perc, curr_profit)

            if time_held >= self.MAX_HOLD_TIME:
                self.logger.warning(f"[!] TIMEOUT! {self.timeout_minutos} minutos. Forçando venda para USDT...")
                if self.manager.sell_alt(current_coin, self.config.BRIDGE):
                    self.last_coin = None
                    self._reset_state_to_bridge(symbol_str, current_coin.symbol)
                return

        self._jump_to_best_coin(current_coin, current_coin_price)

    def bridge_scout(self):
        bridge_balance = self.manager.get_currency_balance(self.config.BRIDGE.symbol, force=True)
        all_24h = self.manager.get_all_tickers_24h()
        for coin in self.db.get_coins():
            if coin.symbol in self.cooldowns:
                if time.time() < self.cooldowns[coin.symbol]: continue 
                else: del self.cooldowns[coin.symbol]

            symbol_str = coin.symbol + self.config.BRIDGE.symbol
            if all_24h.get(symbol_str, -999.0) < self.min_24h_change: continue

            current_coin_price = self.manager.get_ticker_price(coin + self.config.BRIDGE)
            if current_coin_price is None: continue

            ratio_dict = self._get_ratios(coin, current_coin_price)
            if not any(v > 0 for v in ratio_dict.values()):
                if bridge_balance > self.manager.get_min_notional(coin.symbol, self.config.BRIDGE.symbol):
                    self.logger.info(f"Will be purchasing [{coin}] using bridge coin")
                    self.manager.buy_alt(coin, self.config.BRIDGE)
                    return coin
        return None

    def initialize_current_coin(self):
        if self.db.get_current_coin() is None:
            current_coin_symbol = self.config.CURRENT_COIN_SYMBOL
            if current_coin_symbol and current_coin_symbol in self.config.SUPPORTED_COIN_LIST:
                self.db.set_current_coin(current_coin_symbol)
                current_coin = self.db.get_current_coin()
                self.manager.buy_alt(current_coin, self.config.BRIDGE)
            else:
                self.logger.info("Iniciando Smart Start (Bridge Scout) para encontrar a melhor entrada...")

    def _reset_state_to_bridge(self, symbol_str, coin_symbol=None):
        with self.db.db_session() as session: session.query(CurrentCoin).delete()
        self.cached_trade_info.pop(symbol_str, None)
        if coin_symbol:
            self.cooldowns[coin_symbol] = time.time() + (self.cooldown_minutos * 60)
            self.logger.info(f"❄️ {coin_symbol} na geladeira.")
        self.logger.info(f"Dinheiro livre em {self.config.BRIDGE.symbol}. Modo Caçador ativado.")
        