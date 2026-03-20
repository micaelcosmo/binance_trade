from binance_trade_bot.auto_trader import AutoTrader
from binance_trade_bot.models import CurrentCoin
import time
import json

class Strategy(AutoTrader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cached_trade_info = {}
        
        self.STOP_LOSS = -1.6
        self.FEE_MARGIN = 0.4
        self.MAX_HOLD_TIME = 3600
        self.MAX_HANG_TIME = 60

    def initialize(self):
        super().initialize()

    def scout(self):
        start_time = time.time()
        current_coin = self.db.get_current_coin()
        
        if current_coin is None:
            self.logger.info(f"⏳ [RADAR] Aguardando oportunidade com {self.config.BRIDGE.symbol}...")
            with open("bot_status.json", "w") as f:
                json.dump({}, f)
                
            self.bridge_scout()
            return

        symbol_str = current_coin.symbol + self.config.BRIDGE.symbol
        
        try:
            current_price = self.manager.get_ticker_price(symbol_str)
            if current_price is None:
                self.logger.info(f"📡 [AGUARDANDO API] Buscando preço atual de {symbol_str}...")
                return
                
            if symbol_str not in self.cached_trade_info:
                self.logger.info(f"📡 [AGUARDANDO API] Puxando histórico de compra de {symbol_str}...")
                trades = self.manager.binance_client.get_my_trades(symbol=symbol_str, limit=5)
                buy_trades = [t for t in trades if t['isBuyer']]
                
                if buy_trades:
                    last_trade = buy_trades[-1]
                    self.cached_trade_info[symbol_str] = {
                        'price': float(last_trade['price']),
                        'time': int(last_trade['time']) / 1000.0
                    }
                else:
                    self.cached_trade_info[symbol_str] = {'price': current_price, 'time': time.time()}
            
            trade_info = self.cached_trade_info[symbol_str]
            last_buy_price = trade_info['price']
            buy_time = trade_info['time']
            
            profit_margin = float(self.config.SCOUT_MARGIN) 
            target_profit_pct = (self.FEE_MARGIN + profit_margin) / 100
            
            target_price = last_buy_price * (1 + target_profit_pct)
            stop_price = last_buy_price * (1 + (self.STOP_LOSS / 100))
            
            diff_pct = ((current_price / last_buy_price) - 1) * 100
            
            time_held = time.time() - buy_time
            mins_held = int(time_held // 60)
            
            self.logger.info(f"🎯 [HOLD] {current_coin.symbol} | Pago: ${last_buy_price:.5f} | Atual: ${current_price:.5f} ({diff_pct:+.2f}%) | Tempo: {mins_held}m/60m | TP: ${target_price:.5f} | SL: ${stop_price:.5f}")

            status_data = {
                "coin": current_coin.symbol,
                "val_in": f"{last_buy_price:.5f}",
                "val_cur": f"{current_price:.5f}",
                "tp": f"{target_price:.5f}",
                "sl": f"{stop_price:.5f}"
            }
            with open("bot_status.json", "w") as f:
                json.dump(status_data, f)
            
            # Repare que agora passamos 'current_coin.symbol' para a função _reset_state
            if current_price >= target_price:
                self.logger.info(f"[+] TAKE PROFIT! Lucro atingido. Vendendo {current_coin.symbol}...")
                if self.manager.sell_alt(current_coin, self.config.BRIDGE):
                    self._reset_state(symbol_str, current_coin.symbol)
                return
                
            if current_price <= stop_price:
                self.logger.warning(f"[-] STOP LOSS! Queda de {diff_pct:.2f}%. Vendendo {current_coin.symbol}...")
                if self.manager.sell_alt(current_coin, self.config.BRIDGE):
                    self._reset_state(symbol_str, current_coin.symbol)
                return
                
            if time_held >= self.MAX_HOLD_TIME:
                self.logger.warning(f"[!] TIMEOUT! 60 minutos atingidos em {current_coin.symbol}. Liberando capital...")
                if self.manager.sell_alt(current_coin, self.config.BRIDGE):
                    self._reset_state(symbol_str, current_coin.symbol)
                return

            execution_time = time.time() - start_time
            if execution_time > self.MAX_HANG_TIME:
                self.logger.error(f"⚠️ Loop demorou {execution_time:.1f}s. Reiniciando ciclo de segurança!")
                self._reset_state(symbol_str)
                return
                
        except Exception as e:
            self.logger.warning(f"Erro ao avaliar {symbol_str}: {e}")
            self.cached_trade_info.pop(symbol_str, None)

    # Modificamos o reset para aceitar a moeda que será congelada
    def _reset_state(self, symbol_str, coin_symbol=None):
        with self.db.db_session() as session:
            session.query(CurrentCoin).delete()
        self.cached_trade_info.pop(symbol_str, None)
        
        # --- BOTA NA GELADEIRA ---
        if coin_symbol:
            self.cooldowns[coin_symbol] = time.time()
            self.logger.info(f"❄️ {coin_symbol} colocada na geladeira por 30 minutos para forçar a busca de outras moedas.")
        # -------------------------
        
        self.logger.info(f"Dinheiro livre em {self.config.BRIDGE.symbol}. Modo Caçador ativado novamente.")