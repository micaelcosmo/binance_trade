import json
import math
import os
import subprocess
import time
from datetime import datetime, timedelta

import pandas
import pandas_ta
from binance.enums import *

from binance_trade_bot.models.ai_agent import MarketAnalyzer


class Strategy:
    """
    Motor quantitativo principal. Realiza o mapeamento de mercado, calculo de indicadores tecnicos,
    gerenciamento de estado das operacoes e integracao com a IA para tomada de decisao.
    """

    def __init__(self, binance_manager, database_connection, system_logger, system_configuration):
        self.binance_manager = binance_manager
        self.database_connection = database_connection
        self.system_logger = system_logger
        self.system_configuration = system_configuration
        self.binance_client = binance_manager.binance_client
        
        bridge_attribute = getattr(self.system_configuration, 'BRIDGE', 'USDT')
        self.base_coin = getattr(bridge_attribute, 'symbol', bridge_attribute)
        
        self.ai_agent = MarketAnalyzer(self.system_logger)
        self.last_ai_verdict = "Aguardando lote de dados..."
        self.ai_cooldown_until = 0.0
        self.motor_cooldown_minutes = 15
        
        try:
            self.daily_profit_target_pct = float(getattr(self.system_configuration, 'daily_profit_target_pct', 5.0))
            self.max_daily_trades = int(getattr(self.system_configuration, 'max_daily_trades', 3))
            
            self.base_stop_loss_pct = float(getattr(self.system_configuration, 'base_stop_loss_pct', 7.0))
            self.disaster_stop_pct = float(getattr(self.system_configuration, 'disaster_stop_pct', 15.0))
            
            self.trailing_activation_pct = float(getattr(self.system_configuration, 'trailing_activation_pct', 1.5))
            self.trailing_drop_pct = float(getattr(self.system_configuration, 'trailing_drop_pct', 0.3))
            
            ai_cooldown_mins = float(getattr(self.system_configuration, 'ai_cooldown_minutes', 45.0))
            self.golden_rule_cooldown_seconds = ai_cooldown_mins * 60.0
        except Exception as config_error:
            self.system_logger.error(f"Erro na conversao do user.cfg: {config_error}. Assumindo padroes estritos.")
            self.daily_profit_target_pct = 5.0
            self.max_daily_trades = 3
            self.base_stop_loss_pct = 7.0
            self.disaster_stop_pct = 15.0
            self.trailing_activation_pct = 1.5
            self.trailing_drop_pct = 0.3
            self.golden_rule_cooldown_seconds = 2700.0

        self.active_dynamic_stop_loss = 0.0
        self.active_monitor_drop_pct = 0.0 
        
        self.maximum_hold_time_seconds = 7200      
        
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.daily_profit_pct = 0.0
        self.daily_trades = 0
        self.daily_history = []
        self.full_ai_report = "Aguardando primeira analise detalhada da IA..."
        
        self.operation_start_time = 0.0
        self.last_switch_time = 0.0
        self.active_altcoin_quantity = 0.0  
        self.active_buy_price = 0.0
        self.peak_profit_pct = 0.0   
        self.trades_won = 0           
        self.trades_lost = 0          
        self._load_state() 
        
        self.active_current_price = 0.0
        self.active_target_price = 0.0
        self.chart_data_cache = []
        self.last_dossier = []
        self.operation_time_string = "0h 0m"
        
        self.in_operation = False
        self.current_operation_coin = None
        self.hot_cache = []
        self.cold_cache = []
        
        self.system_status_ui = ""
        self.last_heartbeat_ts = 0.0
        self.current_coin_change_pct = 0.0

    def _get_current_version(self):
        try:
            version = subprocess.check_output(
                ["git", "describe", "--tags", "--abbrev=0"], 
                stderr=subprocess.STDOUT, 
                text=True
            ).strip()
            return version
        except Exception:
            return "v3.5.8"

    def _load_state(self):
        if os.path.exists("profit_gain_state.json"):
            try:
                with open("profit_gain_state.json", "r") as file_handler:
                    state_data = json.load(file_handler)
                    self.operation_start_time = state_data.get("operation_start_time", 0.0)
                    self.last_switch_time = state_data.get("last_switch_time", 0.0)
                    self.active_altcoin_quantity = state_data.get("active_altcoin_quantity", 0.0)
                    self.trades_won = state_data.get("trades_won", 0)
                    self.trades_lost = state_data.get("trades_lost", 0)
                    self.active_buy_price = state_data.get("active_buy_price", 0.0)
                    self.peak_profit_pct = state_data.get("peak_profit_pct", 0.0)
                    self.active_dynamic_stop_loss = state_data.get("active_dynamic_stop_loss", 0.0)
                    self.motor_cooldown_minutes = state_data.get("motor_cooldown_minutes", 15)
                    
                    saved_date = state_data.get("current_date", "")
                    if saved_date == datetime.now().strftime("%Y-%m-%d"):
                        self.current_date = saved_date
                        self.daily_profit_pct = state_data.get("daily_profit_pct", 0.0)
                        self.daily_trades = state_data.get("daily_trades", 0)
                        self.daily_history = state_data.get("daily_history", [])
                        self.full_ai_report = state_data.get("full_ai_report", "Aguardando primeira analise detalhada da IA...")
                        self.max_daily_trades = state_data.get("max_daily_trades", self.max_daily_trades)
            except Exception:
                pass

    def _save_state(self):
        try:
            with open("profit_gain_state.json", "w") as file_handler:
                json.dump({
                    "operation_start_time": self.operation_start_time,
                    "last_switch_time": self.last_switch_time,
                    "active_altcoin_quantity": self.active_altcoin_quantity,
                    "trades_won": self.trades_won,
                    "trades_lost": self.trades_lost,
                    "active_buy_price": self.active_buy_price,
                    "peak_profit_pct": self.peak_profit_pct,
                    "active_dynamic_stop_loss": self.active_dynamic_stop_loss,
                    "current_date": self.current_date,
                    "daily_profit_pct": self.daily_profit_pct,
                    "daily_trades": self.daily_trades,
                    "daily_history": self.daily_history,
                    "full_ai_report": self.full_ai_report,
                    "max_daily_trades": self.max_daily_trades,
                    "motor_cooldown_minutes": self.motor_cooldown_minutes
                }, file_handler)
        except Exception as write_error:
            self.system_logger.error(f"Erro ao salvar estado local: {write_error}")

    def _check_daily_reset(self):
        today_date = datetime.now().strftime("%Y-%m-%d")
        if self.current_date != today_date:
            self.current_date = today_date
            self.daily_profit_pct = 0.0
            self.daily_trades = 0
            self.daily_history = []
            self.full_ai_report = "Aguardando primeira analise do novo dia..."
            try:
                self.max_daily_trades = int(getattr(self.system_configuration, 'max_daily_trades', 3))
            except Exception:
                self.max_daily_trades = 3
                
            if not self.in_operation:
                self.system_logger.info("🌅 NOVO DIA: Metas, Historico e Limites foram zerados.")
            self._save_state()

    def _check_ui_flags(self):
        if os.path.exists("cooldown.flag"):
            try:
                with open("cooldown.flag", "r") as f:
                    new_cd = int(f.read().strip())
                self.motor_cooldown_minutes = new_cd
                self.system_logger.info(f"⏱️ [UI OVERRIDE] Intervalo de scan do motor alterado para {new_cd} minutos.")
                self._save_state()
                os.remove("cooldown.flag")
            except Exception:
                pass

        if os.path.exists("reset_trades.flag"):
            self.trades_won = 0
            self.trades_lost = 0
            self.daily_profit_pct = 0.0
            self.daily_trades = 0
            self.daily_history = []
            self.full_ai_report = "Placar zerado. Aguardando nova analise..."
            try:
                self.max_daily_trades = int(getattr(self.system_configuration, 'max_daily_trades', 3))
            except Exception:
                self.max_daily_trades = 3
                
            self._save_state()
            try:
                os.remove("reset_trades.flag")
                self.system_logger.info("♻️ Placar sincronizado com zero no motor!")
            except Exception:
                pass
                
        if os.path.exists("add_trade.flag"):
            self.max_daily_trades += 1
            self.ai_cooldown_until = time.time() + 60
            self.system_logger.warning(f"🟢 [UI OVERRIDE] Limite de trades aumentado para {self.max_daily_trades}! Proxima analise forcada para daqui a 60s.")
            self._save_state()
            try:
                os.remove("add_trade.flag")
            except Exception:
                pass
                
        if os.path.exists("force_sell.flag"):
            try:
                os.remove("force_sell.flag")
                self._execute_forced_sell()
            except Exception as flag_error:
                self.system_logger.error(f"Erro ao acionar flag de venda: {flag_error}")

    def _execute_forced_sell(self):
        if not self.in_operation or not self.current_operation_coin:
            self.system_logger.warning("⚠️ Botao de Venda pressionado, mas o bot nao possui operacao ativa para fechar.")
            return

        market_symbol = f"{self.current_operation_coin}{self.base_coin}"
        self.system_logger.warning(f"🚨 INTERVENCAO MANUAL: Venda forcada acionada para {market_symbol}!")

        try:
            ticker_info = self.binance_client.get_symbol_ticker(symbol=market_symbol)
            current_close_price = float(ticker_info['price'])
            
            drop_percentage = ((current_close_price - self.active_buy_price) / self.active_buy_price) * 100
            
            self._unlock_balance(market_symbol)
            free_balance = self._get_balance(self.current_operation_coin, free_only=True)
            ignore_tick, step_size_val = self.get_precision_filters(market_symbol)
            
            self.binance_client.create_order(
                symbol=market_symbol, 
                side=SIDE_SELL, 
                type=ORDER_TYPE_MARKET, 
                quantity=self.format_decimal(free_balance, step_size_val)
            )
            
            if drop_percentage > 0:
                self.trades_won += 1
                log_reason = f"VENDA_MANUAL (GAIN: {drop_percentage:+.2f}%)"
            else:
                self.trades_lost += 1
                log_reason = f"VENDA_MANUAL (LOSS: {drop_percentage:+.2f}%)"
                
            self.daily_profit_pct += drop_percentage
            self.daily_trades += 1
            
            self.daily_history.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "coin": self.current_operation_coin,
                "result": f"{drop_percentage:+.2f}%",
                "reason": log_reason
            })
            
            self.system_logger.info(f"✅ Venda Forcada concluida com sucesso! P/L da operacao: {drop_percentage:+.2f}%")
            self.system_logger.info("⏱️ Motor em cooldown de 60 segundos antes de retomar as analises.")
            
            self.in_operation = False
            self.current_operation_coin = None
            self.active_monitor_drop_pct = 0.0
            self.active_buy_price = 0.0
            self.active_current_price = 0.0
            self.active_target_price = 0.0
            self.active_altcoin_quantity = 0.0
            self.peak_profit_pct = 0.0
            self.chart_data_cache = []
            self.active_dynamic_stop_loss = 0.0
            self.current_coin_change_pct = 0.0
            
            self.ai_cooldown_until = time.time() + 60
            self._save_state()
            self._write_json_ui()

        except Exception as sell_error:
            self.system_logger.error(f"❌ ERRO CRITICO na Venda Manual: {sell_error}")

    def initialize(self):
        current_version = self._get_current_version()
        self.system_logger.info(f"🚀 Inicializando Profit Gain {current_version.upper()}")
        self._write_json_ui()

    def scout(self):
        self._check_ui_flags()
        self._check_daily_reset()
        
        self.system_status_ui = "" 
        self.scan_market()
        self._write_json_ui()

    def update_values(self):
        self._check_ui_flags()
        self._check_daily_reset()
        
        self.last_heartbeat_ts = time.time() 
        self._write_json_ui()

    def _unlock_balance(self, target_symbol):
        try:
            open_orders_list = self.binance_client.get_open_orders(symbol=target_symbol)
            for order_info in open_orders_list:
                self.system_logger.info(f"🚜 Trator: Cancelando ordem ({order_info['orderId']})...")
                self.binance_client.cancel_order(symbol=target_symbol, orderId=order_info['orderId'])
                time.sleep(0.5) 
        except Exception as unlock_error:
            self.system_logger.error(f"Erro ao limpar ordens travadas: {unlock_error}")

    def _get_balance(self, asset_symbol, free_only=False):
        try:
            balance_data = self.binance_client.get_asset_balance(asset=asset_symbol)
            if free_only:
                return float(balance_data['free'])
            return float(balance_data['free']) + float(balance_data['locked'])
        except Exception as fetch_error:
            self.system_logger.error(f"⚠️ Timeout de rede ao buscar saldo de {asset_symbol}: {fetch_error}")
            return -1.0

    def _retrieve_real_buy_data(self, market_symbol):
        try:
            recent_trades = self.binance_client.get_my_trades(symbol=market_symbol, limit=5)
            if recent_trades:
                last_trade = recent_trades[-1]
                if last_trade['isBuyer']:
                    real_price = float(last_trade['price'])
                    real_timestamp = int(last_trade['time']) / 1000.0
                    return real_price, real_timestamp
        except Exception as history_error:
            self.system_logger.error(f"Erro ao buscar historico: {history_error}")
        return 0.0, 0.0

    def get_precision_filters(self, target_symbol):
        try:
            symbol_info = self.binance_client.get_symbol_info(target_symbol)
            tick_size_val, step_size_val = 0.00000001, 0.00000001
            for filter_item in symbol_info['filters']:
                if filter_item['filterType'] == 'PRICE_FILTER': tick_size_val = float(filter_item['tickSize'])
                if filter_item['filterType'] == 'LOT_SIZE': step_size_val = float(filter_item['stepSize'])
            return tick_size_val, step_size_val
        except Exception:
            return 0.0001, 0.0001

    def format_decimal(self, raw_value, step_size_val):
        precision_lvl = max(0, int(round(-math.log10(float(step_size_val)))))
        precision_factor = 10 ** precision_lvl
        truncated_val = math.floor(float(raw_value) * precision_factor) / precision_factor
        if precision_lvl == 0: return str(int(truncated_val))
        return f"{truncated_val:.{precision_lvl}f}"

    def get_enriched_data(self, target_symbol):
        """ Extrai metricas quantitativas avancadas (Contexto 12h e Bandas de Bollinger). """
        try:
            klines_4h = self.binance_client.get_klines(symbol=target_symbol, interval='4h', limit=30)
            df_4h = pandas.DataFrame(klines_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'trades', 'tbbav', 'tbqav', 'ignore'])
            for col in ['close']: df_4h[col] = pandas.to_numeric(df_4h[col])
            df_4h.ta.rsi(length=14, append=True)
            
            klines_1h = self.binance_client.get_klines(symbol=target_symbol, interval='1h', limit=60)
            df_1h = pandas.DataFrame(klines_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'trades', 'tbbav', 'tbqav', 'ignore'])
            for col in ['open', 'high', 'low', 'close', 'vol']: df_1h[col] = pandas.to_numeric(df_1h[col])
            df_1h.ta.ema(length=21, append=True)
            df_1h.ta.ema(length=9, append=True) 
            df_1h.ta.macd(fast=12, slow=26, signal=9, append=True) 
            df_1h.ta.rsi(length=14, append=True)
            df_1h.ta.atr(length=14, append=True) 
            df_1h.ta.bbands(length=20, std=2, append=True) 
            
            klines_15m = self.binance_client.get_klines(symbol=target_symbol, interval='15m', limit=60)
            df_15m = pandas.DataFrame(klines_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'trades', 'tbbav', 'tbqav', 'ignore'])
            for col in ['open', 'high', 'low', 'close', 'vol']: df_15m[col] = pandas.to_numeric(df_15m[col])
            df_15m.ta.macd(fast=12, slow=26, signal=9, append=True)
            df_15m.ta.rsi(length=14, append=True)
            df_15m.ta.bbands(length=20, std=2, append=True) 
            
            last_row_4h = df_4h.iloc[-1]
            last_row_1h = df_1h.iloc[-1]
            last_row_15m = df_15m.iloc[-1]
            
            current_price = float(last_row_1h['close'])
            
            open_1h = float(last_row_1h['open'])
            close_1h = float(last_row_1h['close'])
            low_1h = float(last_row_1h['low'])
            
            bullish_1h_candle = close_1h > open_1h
            body_1h = abs(close_1h - open_1h)
            bottom_wick_1h = min(open_1h, close_1h) - low_1h
            bottom_rejection_1h = bool(bottom_wick_1h > (body_1h * 1.5))
            
            rsi_4h = float(last_row_4h.get('RSI_14', 50.0))
            rsi_1h = float(last_row_1h.get('RSI_14', 50.0))
            rsi_1h_prev = float(df_1h.iloc[-2].get('RSI_14', 50.0))
            rsi_1h_slope_val = rsi_1h - rsi_1h_prev
            rsi_15m = float(last_row_15m.get('RSI_14', 50.0))
            
            if pandas.isna(rsi_4h): rsi_4h = 50.0
            if pandas.isna(rsi_1h): rsi_1h = 50.0
            if pandas.isna(rsi_15m): rsi_15m = 50.0
            
            macd_hist_1h_current = float(last_row_1h.get('MACDh_12_26_9', 0.0))
            macd_hist_1h_prev = float(df_1h.iloc[-2].get('MACDh_12_26_9', 0.0))
            macd_1h_shifting_up = bool(macd_hist_1h_current > macd_hist_1h_prev)
            macd_histogram_1h_positive = bool(macd_hist_1h_current > 0)

            macd_hist_15m = float(last_row_15m.get('MACDh_12_26_9', 0.0))
            macd_histogram_15m_positive = bool(macd_hist_15m > 0)
            
            ema9_1h = float(last_row_1h.get('EMA_9', 0.0))
            ema21_1h = float(last_row_1h.get('EMA_21', 0.0))
            atr_1h = float(last_row_1h.get('ATRr_14', 0.0))
            
            bullish_15m_micro_candle = bool(last_row_15m['close'] > last_row_15m['open'])
            
            # Novo Radar de Retrovisor: Verifica as ultimas 2 velas de 1H
            touched_lower_band_1h = any(
                bool(float(row['low']) <= float(row.get('BBL_20_2.0', 0.0))) and float(row.get('BBL_20_2.0', 0.0)) > 0
                for _, row in df_1h.tail(2).iterrows()
            )
            
            # Novo Radar de Retrovisor: Verifica as ultimas 3 velas de 15m
            touched_lower_band_15m = any(
                bool(float(row['low']) <= float(row.get('BBL_20_2.0', 0.0))) and float(row.get('BBL_20_2.0', 0.0)) > 0
                for _, row in df_15m.tail(3).iterrows()
            )
            
            try:
                avg_vol_10_candles = df_15m['vol'].tail(11).head(10).mean()
                current_vol_candle = df_15m['vol'].iloc[-1]
                volume_15m_above_avg = bool(current_vol_candle > avg_vol_10_candles)
            except Exception:
                volume_15m_above_avg = False

            ema21_1h_distance_pct = ((current_price - ema21_1h) / ema21_1h) * 100 if ema21_1h > 0 else 0.0
            price_vs_ema9_1h_pct = ((current_price - ema9_1h) / ema9_1h) * 100 if ema9_1h > 0 else 0.0
            
            price_action_1h_last_12 = [
                {"h": float(df_1h.iloc[-i]['high']), "l": float(df_1h.iloc[-i]['low']), "c": float(df_1h.iloc[-i]['close'])}
                for i in range(12, 0, -1)
            ]

            current_atr_pct = (atr_1h / current_price) * 100 if current_price > 0 else 0.0
            required_atr_bottom_pct = -(current_atr_pct * 2.0)
            
            try:
                ticker_data = self.binance_client.get_ticker(symbol=target_symbol)
                change_24h_pct = float(ticker_data['priceChangePercent'])
                open_price_val = float(ticker_data['openPrice'])
                low_price_val = float(ticker_data['lowPrice'])
                min_24h_change_pct = ((low_price_val - open_price_val) / open_price_val) * 100 if open_price_val > 0 else 0.0
                volume_24h_usdt = float(ticker_data.get('quoteVolume', 0.0)) 
            except Exception:
                change_24h_pct = 0.0
                min_24h_change_pct = 0.0
                volume_24h_usdt = 0.0

            dynamic_stop_val = current_atr_pct * 4.0 
            if "BTC" in target_symbol:
                dynamic_stop_val = max(6.0, min(dynamic_stop_val, 10.50))
            else:
                dynamic_stop_val = max(4.0, min(dynamic_stop_val, self.base_stop_loss_pct)) 
            
            ai_payload_dict = {
                "coin": target_symbol.replace(self.base_coin, ""),
                "current_price": current_price,
                "bullish_1h_candle": bullish_1h_candle,
                "bottom_rejection_1h": bottom_rejection_1h,
                "price_action_1h_last_12": price_action_1h_last_12, 
                "macd_1h_shifting_up": macd_1h_shifting_up, 
                "macd_histogram_1h_positive": macd_histogram_1h_positive, 
                "touched_lower_band_1h": touched_lower_band_1h,
                "touched_lower_band_15m": touched_lower_band_15m,
                "rsi_1h_slope": round(rsi_1h_slope_val, 2), 
                "rsi_MACRO_4h": round(rsi_4h, 2),
                "rsi_INTER_1h": round(rsi_1h, 2),
                "rsi_MICRO_15m": round(rsi_15m, 2), 
                "macd_histogram_15m_positive": macd_histogram_15m_positive,
                "change_24h_pct": f"{change_24h_pct:+.2f}%",
                "min_24h_change_pct": f"{min_24h_change_pct:+.2f}%",
                "required_atr_bottom_pct": f"{required_atr_bottom_pct:+.2f}%",
                "bullish_15m_micro_candle": bullish_15m_micro_candle,
                "volume_24h_usdt": round(volume_24h_usdt, 2),
                "volume_15m_above_avg": volume_15m_above_avg,
                "ema21_1h_distance_pct": f"{ema21_1h_distance_pct:+.2f}%",
                "price_vs_ema9_1h_pct": f"{price_vs_ema9_1h_pct:+.2f}%", 
                "suggested_atr_stop_loss": round(dynamic_stop_val, 2)
            }
            
            is_uptrend = current_price > ema21_1h
            return ai_payload_dict, is_uptrend
        except Exception as fetch_error:
            error_string = str(fetch_error)
            if "Connection" in error_string or "10054" in error_string or "NameResolution" in error_string or "Timeout" in error_string:
                raise ConnectionError(f"Network Drop: {error_string}")
            self.system_logger.error(f"Erro na extração de métricas de {target_symbol}: {fetch_error}")
            return None, False

    def execute_real_trade(self, coin_symbol, target_price, calculated_atr_stop):
        market_symbol = f"{coin_symbol}{self.base_coin}"
        available_base_balance = self._get_balance(self.base_coin)
        
        if available_base_balance < 5.1: 
            self.system_logger.warning(f"⚠️ VETO DA CORRETORA: A IA aprovou {coin_symbol}, mas seu saldo livre de {self.base_coin} é ${available_base_balance:.2f} (Mínimo Binance: $5.10).")
            return False

        try:
            self.system_logger.info(f"🚀 ENTRADA REAL: Comprando {market_symbol} a mercado...")
            ignore_tick, step_size_val = self.get_precision_filters(market_symbol)
            
            buy_qty_usdt = available_base_balance * 0.99 
            quote_qty_str = self.format_decimal(buy_qty_usdt, 0.01) 
            
            self.binance_client.create_order(symbol=market_symbol, side=SIDE_BUY, type=ORDER_TYPE_MARKET, quoteOrderQty=quote_qty_str)
            time.sleep(2) 
            
            purchased_coin_balance = self._get_balance(coin_symbol)
            sell_qty_str = self.format_decimal(purchased_coin_balance, step_size_val)
            
            if float(sell_qty_str) == 0: return True

            self.system_logger.info(f"✅ Compra confirmada! Armando Trailing Stop invisível (+{self.trailing_activation_pct:.2f}%) | Stop Tolerante: -{calculated_atr_stop:.2f}%")
            
            self.operation_start_time = time.time()
            self.active_altcoin_quantity = float(sell_qty_str)
            self.active_buy_price = float(target_price)
            self.peak_profit_pct = 0.0
            self.active_target_price = float(target_price) * (1 + (self.trailing_activation_pct / 100))
            self.active_dynamic_stop_loss = float(calculated_atr_stop)
            self.last_switch_time = time.time()
            self.current_coin_change_pct = 0.0
            self._save_state()
            
            self.active_current_price = float(target_price)
            self.operation_time_string = "0h 0m"
            self._write_json_ui() 
            
            return True

        except Exception as execution_error:
            self.system_logger.error(f"❌ ERRO CRÍTICO no roteamento de ordem: {execution_error}")
            return False

    def _print_ai_verdict(self, text_summary):
        lines = str(text_summary).split('\n')
        if not lines: return
        self.system_logger.info(f"🧠 Parecer da IA    : {lines[0].strip()}")
        for line in lines[1:]:
            if line.strip():
                self.system_logger.info(f"                      {line.strip()}")

    def scan_market(self):
        if not self.in_operation:
            if self.daily_profit_pct >= self.daily_profit_target_pct or self.daily_trades >= self.max_daily_trades:
                time_now = datetime.now()
                tomorrow_date = time_now + timedelta(days=1)
                midnight_time = datetime(tomorrow_date.year, tomorrow_date.month, tomorrow_date.day, 0, 0, 0)
                seconds_to_midnight = (midnight_time - time_now).total_seconds()
                
                self.system_logger.warning(f"🏆 META BATIDA OU LIMITE DE TRADES! Lucro: +{self.daily_profit_pct:.2f}% | Trades: {self.daily_trades}/{self.max_daily_trades}")
                self.system_logger.info("💤 Sistema entrando em hibernação institucional até a meia-noite.")
                self.ai_cooldown_until = time.time() + seconds_to_midnight
                return

        temp_hot_list = []
        temp_cold_list = []
        ai_batch_payload = []
        dossier_cache = []
        
        try:
            account_data = self.binance_client.get_account()
            balances_dict = {balance_info['asset']: float(balance_info['free']) + float(balance_info['locked']) for balance_info in account_data['balances']}
        except Exception:
            balances_dict = {}

        self.system_status_ui = "Minerando métricas do mercado..."

        for check_coin in self.system_configuration.SUPPORTED_COIN_LIST:
            if check_coin == self.base_coin: continue
            
            market_symbol = f"{check_coin}{self.base_coin}"
            
            try:
                enriched_data, is_uptrend = self.get_enriched_data(market_symbol)
            except ConnectionError:
                self.system_status_ui = "⚠️ Conexão instável. Ignorando ativo na iteração..."
                continue 
                
            if enriched_data:
                aligned_coin_str = f"{check_coin: <7}"
                ui_line_text = f"💼 {aligned_coin_str}: ${enriched_data['current_price']:.4f} ({enriched_data['change_24h_pct']})"
                
                if is_uptrend: temp_hot_list.append(ui_line_text)
                else: temp_cold_list.append(ui_line_text)

                try:
                    cur_change_flt = float(str(enriched_data.get('change_24h_pct', '0')).replace('%', '').replace('+', ''))
                    min_change_flt = float(str(enriched_data.get('min_24h_change_pct', '0')).replace('%', '').replace('+', ''))
                    req_bottom_flt = float(str(enriched_data.get('required_atr_bottom_pct', '0')).replace('%', '').replace('+', ''))
                    
                    bollinger_ok = enriched_data.get('touched_lower_band_1h', False) or enriched_data.get('touched_lower_band_15m', False)
                    
                    if min_change_flt <= req_bottom_flt and -self.disaster_stop_pct <= cur_change_flt <= 2.50:
                        dossier_cache.append(enriched_data)
                        if bollinger_ok:
                            ai_batch_payload.append(enriched_data)
                except Exception:
                    pass

        self.hot_cache = sorted(temp_hot_list)
        self.cold_cache = sorted(temp_cold_list)
        
        if not self.in_operation and dossier_cache:
            self.last_dossier = dossier_cache

        if not self.in_operation:
            self.active_current_price, self.active_target_price = 0.0, 0.0
            self.chart_data_cache = []
            self.operation_time_string = "0h 0m"
            base_coin_balance = balances_dict.get(self.base_coin, 0.0)
            
            if base_coin_balance < 5.0:
                coin_scan_order = ["BTC"] + [check_coin for check_coin in self.system_configuration.SUPPORTED_COIN_LIST if check_coin not in ["BTC", self.base_coin]]
                for check_coin in coin_scan_order:
                    coin_qty = balances_dict.get(check_coin, 0.0)
                    if coin_qty > 0:
                        try:
                            ticker_data = self.binance_client.get_symbol_ticker(symbol=f"{check_coin}{self.base_coin}")
                            converted_usd_val = coin_qty * float(ticker_data['price'])
                            if converted_usd_val >= 5.0:
                                self.system_logger.info(f"🔄 Recuperação de Estado: Assumindo controle de {check_coin}.")
                                self.in_operation = True
                                self.current_operation_coin = check_coin
                                self.active_altcoin_quantity = coin_qty
                                if getattr(self, 'operation_start_time', 0.0) == 0.0:
                                    self.operation_start_time = time.time()
                                    self.last_switch_time = time.time()
                                self._save_state()
                                break
                        except Exception: pass

        if self.in_operation:
            market_symbol = f"{self.current_operation_coin}{self.base_coin}"
            
            try:
                klines_hist = self.binance_client.get_klines(symbol=market_symbol, interval='15m', limit=50)
                df_chart = pandas.DataFrame(klines_hist, columns=['timestamp', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'trades', 'tbbav', 'tbqav', 'ignore'])
                for col in ['open', 'high', 'low', 'close']: df_chart[col] = pandas.to_numeric(df_chart[col])
                df_chart.ta.bbands(length=20, std=2, append=True)
                
                df_last_30 = df_chart.tail(30)
                new_cache = []
                for _, row in df_last_30.iterrows():
                    new_cache.append({
                        "o": float(row['open']),
                        "h": float(row['high']),
                        "l": float(row['low']),
                        "c": float(row['close']),
                        "bbu": float(row.get('BBU_20_2.0', row['high'])),
                        "bbm": float(row.get('BBM_20_2.0', row['close'])),
                        "bbl": float(row.get('BBL_20_2.0', row['low']))
                    })
                self.chart_data_cache = new_cache
            except Exception as e: 
                pass

            try:
                ticker_data = self.binance_client.get_ticker(symbol=market_symbol)
                self.active_current_price = float(ticker_data['lastPrice'])
                self.current_coin_change_pct = float(ticker_data['priceChangePercent'])
                
                operated_coin_balance = self._get_balance(self.current_operation_coin)

                if operated_coin_balance < 0:
                    return 

                if (operated_coin_balance * self.active_current_price) < 5.0:
                    self.system_logger.info(f"✅ Saldo insuficiente em {self.current_operation_coin}. Operação categorizada como finalizada.")
                    self.in_operation = False
                    self.current_operation_coin = None
                    self.active_monitor_drop_pct, self.active_buy_price, self.active_current_price, self.active_target_price, self.active_altcoin_quantity, self.peak_profit_pct = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                    self.chart_data_cache = []
                    self.active_dynamic_stop_loss = 0.0
                    self.current_coin_change_pct = 0.0
                    self._save_state()
                    return

                if self.active_buy_price <= 0:
                    real_price, real_timestamp = self._retrieve_real_buy_data(market_symbol)
                    if real_price > 0:
                        self.active_buy_price = real_price
                        if getattr(self, 'operation_start_time', 0) <= 0:
                            self.operation_start_time = real_timestamp
                            self.last_switch_time = time.time()
                    else:
                        self.active_buy_price = self.active_current_price
                    self._save_state()

                drop_percentage = ((self.active_current_price - self.active_buy_price) / self.active_buy_price) * 100
                self.active_monitor_drop_pct = drop_percentage
                
                if drop_percentage > self.peak_profit_pct:
                    self.peak_profit_pct = drop_percentage
                    self._save_state()

                if self.peak_profit_pct >= self.trailing_activation_pct:
                    trigger_sell_pct = self.peak_profit_pct - self.trailing_drop_pct
                    self.active_target_price = self.active_buy_price * (1 + (trigger_sell_pct / 100))
                else:
                    self.active_target_price = self.active_buy_price * (1 + (self.trailing_activation_pct / 100))

                active_seconds_op = time.time() - self.operation_start_time
                active_hours = int(active_seconds_op // 3600)
                active_minutes = int((active_seconds_op % 3600) // 60)
                locked_time_hours = active_seconds_op / 3600.0
                
                seconds_since_switch = time.time() - self.last_switch_time
                cooldown_remaining_sec = self.golden_rule_cooldown_seconds - seconds_since_switch
                cooldown_status_str = f" (Tribunal: {int(cooldown_remaining_sec//3600)}h {int((cooldown_remaining_sec%3600)//60)}m)" if cooldown_remaining_sec > 0 else " (Tribunal: Pronta)"
                self.operation_time_string = f"{active_hours}h {active_minutes}m{cooldown_status_str}"
                
                self.system_status_ui = f"Em Operação ({self.current_operation_coin})"

                is_selling_now = False
                executed_sell_reason = ""
                
                current_sl_limit = self.active_dynamic_stop_loss if self.active_dynamic_stop_loss > 0 else self.base_stop_loss_pct

                if drop_percentage <= -self.disaster_stop_pct:
                    is_selling_now = True
                    executed_sell_reason = "STOP_DESASTRE"
                    self.system_logger.warning(f"🚨 DESASTRE ABSOLUTO ACIONADO! Moeda perdeu {self.disaster_stop_pct}% de valor em carteira. Cortando risco sistêmico.")
                elif drop_percentage <= -current_sl_limit:
                    is_selling_now = True
                    executed_sell_reason = "STOP_LOSS_DINAMICO"
                    self.system_logger.warning(f"🚨 STOP LOSS DINÂMICO ACIONADO para {self.current_operation_coin}! Queda de {drop_percentage:.2f}%")
                
                elif self.peak_profit_pct >= self.trailing_activation_pct and (self.peak_profit_pct - drop_percentage) >= self.trailing_drop_pct:
                    is_selling_now = True
                    executed_sell_reason = "TAKE_PROFIT"
                    self.system_logger.info(f"✅ TAKE PROFIT TRAILING ACIONADO para {self.current_operation_coin}! Pico: {self.peak_profit_pct:.2f}% | Fechado em: {drop_percentage:.2f}%")

                if is_selling_now:
                    self._unlock_balance(market_symbol) 
                    available_free_balance = self._get_balance(self.current_operation_coin, free_only=True)
                    ignore_tick, step_size_val = self.get_precision_filters(market_symbol)
                    
                    self.binance_client.create_order(symbol=market_symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=self.format_decimal(available_free_balance, step_size_val))
                    
                    if "STOP" in executed_sell_reason: 
                        self.trades_lost += 1
                    else: 
                        self.trades_won += 1
                    
                    self.daily_profit_pct += drop_percentage
                    self.daily_trades += 1
                    
                    self.daily_history.append({
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "coin": self.current_operation_coin,
                        "result": f"{drop_percentage:+.2f}%",
                        "reason": executed_sell_reason
                    })
                    
                    self.in_operation = False
                    self.current_operation_coin = None
                    self.active_monitor_drop_pct, self.active_buy_price, self.active_current_price, self.active_target_price, self.active_altcoin_quantity, self.peak_profit_pct = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                    self.chart_data_cache = []
                    self.active_dynamic_stop_loss = 0.0
                    self.current_coin_change_pct = 0.0
                    self._save_state()
                else:
                    if drop_percentage < -0.15 and cooldown_remaining_sec <= 0:
                        if drop_percentage < -2.50:
                            self.last_switch_time = time.time()
                            self._save_state()
                        else:
                            if locked_time_hours >= 10.0:
                                swap_payload = []
                                for asset in ai_batch_payload:
                                    if asset['coin'] != self.current_operation_coin:
                                        try:
                                            cur_change_str = str(asset.get('change_24h_pct', '0')).replace('%', '').replace('+', '')
                                            min_change_str = str(asset.get('min_24h_change_pct', '0')).replace('%', '').replace('+', '')
                                            req_bottom_str = str(asset.get('required_atr_bottom_pct', '0')).replace('%', '').replace('+', '')
                                            
                                            if float(min_change_str) <= float(req_bottom_str) and float(cur_change_str) <= -0.50:
                                                bollinger_ok = asset.get('touched_lower_band_1h', False) or asset.get('touched_lower_band_15m', False)
                                                if bollinger_ok:
                                                    swap_payload.append(asset)
                                        except Exception: pass
                                
                                if len(swap_payload) >= 4:
                                    self.system_status_ui = "⏳ Convocando TRIBUNAL DE SWAP..."
                                    swap_analysis = self.ai_agent.analyze_swap(swap_payload, self.current_operation_coin, drop_percentage, locked_time_hours)
                                    winning_swap_coin = swap_analysis.get("winning_coin", "HOLD")
                                    
                                    if winning_swap_coin == "ERROR_503":
                                        self.system_status_ui = "⚠️ IA sobrecarregada. Nova tentativa em 5 min."
                                        self.last_switch_time = time.time() - self.golden_rule_cooldown_seconds + 300 
                                        return
                                        
                                    ai_confidence = swap_analysis.get("final_confidence", 0)
                                    swap_decision_desc = swap_analysis.get("decision_summary", "Decisão mantida em HOLD.")
                                    
                                    if winning_swap_coin not in ["HOLD", "NENHUMA"] and ai_confidence >= 95:
                                        chosen_asset = next((item for item in swap_payload if item['coin'] == winning_swap_coin), None)
                                        if chosen_asset:
                                            target_swap_price = chosen_asset['current_price']
                                            target_swap_stop_atr = chosen_asset['suggested_atr_stop_loss']
                                            
                                            self.system_logger.warning(f"👑 TRIBUNAL APROVOU SWAP! Assumindo prejuízo para migrar com {ai_confidence}% de chance para {winning_swap_coin}.")
                                            
                                            self.full_ai_report = f"[{datetime.now().strftime('%H:%M:%S')}]\n\n⚖️ TRIBUNAL DE SWAP APROVADO\n🏆 Vencedora: {winning_swap_coin} ({ai_confidence}%)\n\n🧠 Parecer:\n{swap_decision_desc}"
                                            self._print_ai_verdict(swap_decision_desc)
                                            
                                            self._unlock_balance(market_symbol) 
                                            available_free_balance = self._get_balance(self.current_operation_coin, free_only=True)
                                            ignore_tick, step_size_val = self.get_precision_filters(market_symbol)
                                            
                                            self.binance_client.create_order(symbol=market_symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=self.format_decimal(available_free_balance, step_size_val))
                                            time.sleep(2)
                                            
                                            self.trades_lost += 1 
                                            self.daily_profit_pct += drop_percentage 
                                            self.daily_trades += 1
                                            
                                            self.daily_history.append({
                                                "time": datetime.now().strftime("%H:%M:%S"),
                                                "coin": self.current_operation_coin,
                                                "result": f"{drop_percentage:+.2f}%",
                                                "reason": "SWAP_IA_95%"
                                            })
                                            
                                            self.last_switch_time = time.time()
                                            self.in_operation = False 
                                            self._save_state()
                                            
                                            if target_swap_price > 0 and self.execute_real_trade(winning_swap_coin, target_swap_price, target_swap_stop_atr):
                                                self.in_operation = True
                                                self.current_operation_coin = winning_swap_coin
                                        return
                                    else:
                                        self.system_logger.info(f"🛡️ TRIBUNAL ORDENOU HOLD. Critérios rigorosos de confiança (95%+) não atingidos.")
                                        self.full_ai_report = f"[{datetime.now().strftime('%H:%M:%S')}]\n\n🛡️ TRIBUNAL DE SWAP RECUSADO (HOLD)\n⚖️ Veredito: Nenhuma moeda com 95%+ de chance detectada. Segurando {self.current_operation_coin}.\n\n🧠 Parecer:\n{swap_decision_desc}"
                                        self._print_ai_verdict(swap_decision_desc)
                                        self.last_switch_time = time.time() 
                                        self._save_state()
                                else:
                                    self.last_switch_time = time.time() 

            except Exception as monitoring_error:
                self.system_logger.error(f"Exceção capturada no monitoramento dinâmico: {monitoring_error}")

        else:
            current_time = time.time()
            if current_time < self.ai_cooldown_until:
                self.system_status_ui = "Aguardando próxima análise..."
                return

            if ai_batch_payload:
                self.system_status_ui = "Aguardando veredito da IA..."
                self.system_logger.info(f"🟢 Submetendo Dossiê com {len(ai_batch_payload)} ativos ao Comitê de IA...")
                ai_agent_analysis = self.ai_agent.analyze_batch(ai_batch_payload)
                
                ai_winning_coin = ai_agent_analysis.get("winning_coin", "NENHUMA")
                
                if ai_winning_coin == "ERROR_503":
                    self.system_status_ui = "⚠️ IA sobrecarregada. Nova tentativa em 5 min."
                    self.ai_cooldown_until = time.time() + 300
                    return
                    
                ai_final_confidence = ai_agent_analysis.get("final_confidence", 0)
                ai_decision_summary = ai_agent_analysis.get("decision_summary", "Sem motivo específico.")

                self.system_logger.info("================ RELATÓRIO DA HORA ===================")
                self.system_logger.info(f"📋 Ativos Analisados : {len(ai_batch_payload)} moedas")
                self.system_logger.info(f"🏆 Vencedor Avaliado: {ai_winning_coin} (Confiança: {ai_final_confidence}%)")
                self._print_ai_verdict(ai_decision_summary)
                self.system_logger.info("======================================================")

                self.full_ai_report = f"[{datetime.now().strftime('%H:%M:%S')}]\n\n🏆 Vencedora Avaliada: {ai_winning_coin} ({ai_final_confidence}%)\n\n🧠 Parecer Detalhado Institucional:\n{ai_decision_summary}"

                if ai_winning_coin != "NENHUMA" and ai_final_confidence >= 90:
                    self.last_ai_verdict = f"✅ COMPRA {ai_winning_coin} ({ai_final_confidence}%): {ai_decision_summary.splitlines()[0]}"
                    
                    chosen_asset = next((item for item in ai_batch_payload if item['coin'] == ai_winning_coin), None)
                    if chosen_asset:
                        target_price = chosen_asset['current_price']
                        target_stop_atr = chosen_asset['suggested_atr_stop_loss']
                        
                        trade_executed = self.execute_real_trade(ai_winning_coin, target_price, target_stop_atr)
                        if trade_executed:
                            self.in_operation = True
                            self.current_operation_coin = ai_winning_coin
                else:
                    first_line_reason = ai_decision_summary.split('\n')[0] if ai_decision_summary else "Veto de entrada."
                    self.last_ai_verdict = f"🛑 MERCADO VETADO: {first_line_reason}"
                    self.ai_cooldown_until = time.time() + self.golden_rule_cooldown_seconds
                    
            else:
                self.system_logger.info("🛑 [FILTRO PRÉVIO] Nenhum ativo atendeu aos critérios matemáticos mínimos (Queda ATR + Bollinger Inferior).")
                self.system_logger.info("================ RELATÓRIO DA HORA ===================")
                self.system_logger.info(f"📋 Ativos Analisados : {len(self.last_dossier)} moedas (Dossiê retido)")
                self.system_logger.info("🏆 Vencedor Avaliado: NENHUMA (Retido no Motor)")
                self.system_logger.info("🧠 Parecer do Motor : Nenhuma moeda cumpriu o filtro de exaustão estatística.")
                self.system_logger.info("======================================================")

                self.full_ai_report = f"[{datetime.now().strftime('%H:%M:%S')}]\n\n🛑 VETADO PELO MOTOR PYTHON\n\nNenhum ativo do mercado tocou na banda inferior de Bollinger (15m ou 1H) neste ciclo. Dossiê retido na camada matemática para economizar recursos da API."
                self.last_ai_verdict = "🛑 MERCADO VETADO: Filtro Matemático (Sem Agulhada)."
                self.system_status_ui = "Aguardando próxima análise..."
                self.ai_cooldown_until = time.time() + (self.motor_cooldown_minutes * 60)

    def _write_json_ui(self):
        try:
            btc_ticker_data = self.binance_client.get_ticker(symbol=f"BTC{self.base_coin}")
            btc_price_val = float(btc_ticker_data['lastPrice'])
            btc_change_val = float(btc_ticker_data['priceChangePercent'])
        except Exception:
            btc_price_val, btc_change_val = 0.0, 0.0
            
        target_text = f" | 📅 Diário: {self.daily_profit_pct:+.2f}% ({self.daily_trades}/{self.max_daily_trades} Trades)"
        
        status_text = self.system_status_ui if self.system_status_ui else "Processando métricas..."
        
        if self.in_operation:
            display_current_sl = self.active_dynamic_stop_loss if self.active_dynamic_stop_loss > 0 else self.base_stop_loss_pct
            if self.peak_profit_pct >= self.trailing_activation_pct:
                centered_detail = f"[⏳] Duração: {self.operation_time_string} | 🚀 TRAILING ATIVO! Pico: {self.peak_profit_pct:.2f}% | Trava: {self.peak_profit_pct - self.trailing_drop_pct:.2f}%{target_text}"
            else:
                centered_detail = f"[⏳] Duração: {self.operation_time_string} | [🎯] Gatilho Trailing: {self.trailing_activation_pct:.2f}% | [🛑] SL: -{display_current_sl:.2f}% (Var: {self.active_monitor_drop_pct:+.2f}%){target_text}"
        else:
            if self.daily_profit_pct >= self.daily_profit_target_pct or self.daily_trades >= self.max_daily_trades:
                centered_detail = f"💤 HIBERNAÇÃO ATIVA: Metas ou limites atingidos. Retorno à meia-noite.{target_text}"
                status_text = "Hibernação Institucional"
            else:
                centered_detail = f"🧠 ÚLTIMO VEREDITO: {self.last_ai_verdict}{target_text}"
            
        state_data_payload = {
            "coin": self.current_operation_coin if self.in_operation else self.base_coin,
            "status": status_text,
            "cooldown_until": self.ai_cooldown_until,
            "last_heartbeat_ts": self.last_heartbeat_ts,
            "current_coin_change": self.current_coin_change_pct,
            "btc_price": btc_price_val,
            "btc_change": btc_change_val,
            "buy_price": self.active_buy_price,
            "current_price": self.active_current_price,
            "target_price": self.active_target_price,
            "active_qty": self.active_altcoin_quantity,          
            "buy_time": self.operation_start_time,         
            "chart_data": self.chart_data_cache,
            "trades_won": self.trades_won,     
            "trades_lost": self.trades_lost,   
            "current_detail": centered_detail,
            "hot_cache": self.hot_cache,
            "cold_cache": self.cold_cache,
            "daily_trades": self.daily_trades,
            "max_daily_trades": self.max_daily_trades,
            "full_ai_report": self.full_ai_report,
            "daily_history": self.daily_history,
            "last_dossier": self.last_dossier,
            "motor_cooldown_minutes": self.motor_cooldown_minutes
        }

        try:
            with open("bot_status.json", "w", encoding="utf-8") as file_handler: 
                json.dump(state_data_payload, file_handler, ensure_ascii=False, indent=2)
        except Exception:
            pass