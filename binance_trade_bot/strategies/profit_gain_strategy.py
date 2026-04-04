import time
import json
import math
import os
import pandas
import pandas_ta
from datetime import datetime, timedelta

from binance.enums import *
from binance_trade_bot.models.ai_agent import MarketAnalyzer


class Strategy:
    def __init__(self, binance_manager, database_connection, system_logger, system_configuration):
        self.binance_manager = binance_manager
        self.database_connection = database_connection
        self.system_logger = system_logger
        self.system_configuration = system_configuration
        self.binance_client = binance_manager.binance_client
        
        bridge_attribute = getattr(self.system_configuration, 'BRIDGE', 'USDT')
        self.base_coin = getattr(bridge_attribute, 'symbol', bridge_attribute)
        
        self.ai_agent = MarketAnalyzer(self.system_logger)
        self.ultimo_veredito_ia = "Aguardando lote de dados..."
        self.ai_cooldown_until = 0.0
        
        self.trailing_activation_percentage = 1.50 
        self.trailing_drop_percentage = 0.30
        
        self.stop_loss_percentage_base = 3.00 
        self.stop_loss_dinamico_ativo = 0.0
        self.stop_loss_monitor_drop = 0.0 
        
        self.maximum_hold_time_seconds = 7200      
        self.golden_rule_cooldown_seconds = 7200 
        
        self.data_atual = datetime.now().strftime("%Y-%m-%d")
        self.lucro_diario_pct = 0.0
        self.trades_no_dia = 0
        self.max_trades_diario = 3
        self.historico_diario = []
        self.relatorio_ia_completo = "Aguardando primeira análise detalhada da IA..."
        
        self.operation_start_time = 0.0
        self.last_switch_time = 0.0
        self.quantidade_altcoin_ativa = 0.0  
        self.preco_compra_ativo = 0.0
        self.peak_profit_percentage = 0.0   
        self.trades_won = 0           
        self.trades_lost = 0          
        self._load_state() 
        
        self.preco_atual_ativo = 0.0
        self.preco_alvo_ativo = 0.0
        self.chart_data_cache = []
        self.tempo_operacao_string = "0h 0m"
        
        self.em_operacao = False
        self.moeda_atual_operacao = None
        self.aptas_cache = []
        self.geladeira_cache = []

    def _load_state(self):
        if os.path.exists("profit_gain_state.json"):
            try:
                with open("profit_gain_state.json", "r") as file_handler:
                    state_data = json.load(file_handler)
                    self.operation_start_time = state_data.get("operation_start_time", 0.0)
                    self.last_switch_time = state_data.get("last_switch_time", 0.0)
                    self.quantidade_altcoin_ativa = state_data.get("quantidade_altcoin_ativa", 0.0)
                    self.trades_won = state_data.get("trades_won", 0)
                    self.trades_lost = state_data.get("trades_lost", 0)
                    self.preco_compra_ativo = state_data.get("preco_compra_ativo", 0.0)
                    self.peak_profit_percentage = state_data.get("peak_profit_percentage", 0.0)
                    self.stop_loss_dinamico_ativo = state_data.get("stop_loss_dinamico_ativo", 0.0)
                    
                    data_salva = state_data.get("data_atual", "")
                    if data_salva == datetime.now().strftime("%Y-%m-%d"):
                        self.data_atual = data_salva
                        self.lucro_diario_pct = state_data.get("lucro_diario_pct", 0.0)
                        self.trades_no_dia = state_data.get("trades_no_dia", 0)
                        self.max_trades_diario = state_data.get("max_trades_diario", 3)
                        self.historico_diario = state_data.get("historico_diario", [])
                        self.relatorio_ia_completo = state_data.get("relatorio_ia_completo", "Aguardando primeira análise detalhada da IA...")
            except Exception:
                pass

    def _save_state(self):
        try:
            with open("profit_gain_state.json", "w") as file_handler:
                json.dump({
                    "operation_start_time": self.operation_start_time,
                    "last_switch_time": self.last_switch_time,
                    "quantidade_altcoin_ativa": self.quantidade_altcoin_ativa,
                    "trades_won": self.trades_won,
                    "trades_lost": self.trades_lost,
                    "preco_compra_ativo": self.preco_compra_ativo,
                    "peak_profit_percentage": self.peak_profit_percentage,
                    "stop_loss_dinamico_ativo": self.stop_loss_dinamico_ativo,
                    "data_atual": self.data_atual,
                    "lucro_diario_pct": self.lucro_diario_pct,
                    "trades_no_dia": self.trades_no_dia,
                    "max_trades_diario": self.max_trades_diario,
                    "historico_diario": self.historico_diario,
                    "relatorio_ia_completo": self.relatorio_ia_completo
                }, file_handler)
        except Exception as erro_escrita:
            self.system_logger.error(f"Erro ao salvar estado local: {erro_escrita}")

    def _check_daily_reset(self):
        hoje = datetime.now().strftime("%Y-%m-%d")
        if self.data_atual != hoje:
            self.data_atual = hoje
            self.lucro_diario_pct = 0.0
            self.trades_no_dia = 0
            self.max_trades_diario = 3
            self.historico_diario = []
            self.relatorio_ia_completo = "Aguardando primeira análise do novo dia..."
            if not self.em_operacao:
                self.system_logger.info("🌅 NOVO DIA: Metas, Histórico e Limites foram zerados.")
            self._save_state()

    def _check_ui_flags(self):
        if os.path.exists("reset_trades.flag"):
            self.trades_won = 0
            self.trades_lost = 0
            self.lucro_diario_pct = 0.0
            self.trades_no_dia = 0
            self.max_trades_diario = 3
            self.historico_diario = []
            self.relatorio_ia_completo = "Placar zerado. Aguardando nova análise..."
            self._save_state()
            try:
                os.remove("reset_trades.flag")
                self.system_logger.info("♻️ Placar sincronizado com zero no motor!")
            except Exception:
                pass
                
        if os.path.exists("add_trade.flag"):
            self.max_trades_diario += 1
            self.system_logger.warning(f"🟢 [UI OVERRIDE] Limite de trades de hoje aumentado para {self.max_trades_diario}!")
            self._save_state()
            try:
                os.remove("add_trade.flag")
            except Exception:
                pass
                
        # V3.3.0: Interceptador do Panic Button
        if os.path.exists("force_sell.flag"):
            try:
                os.remove("force_sell.flag")
                self._execute_forced_sell()
            except Exception as e:
                self.system_logger.error(f"Erro ao acionar flag de venda: {e}")

    def _execute_forced_sell(self):
        if not self.em_operacao or not self.moeda_atual_operacao:
            self.system_logger.warning("⚠️ Botão de Venda pressionado, mas o bot não possui operação ativa para fechar.")
            return

        market_symbol = f"{self.moeda_atual_operacao}{self.base_coin}"
        self.system_logger.warning(f"🚨 INTERVENÇÃO MANUAL: Venda forçada acionada para {market_symbol}!")

        try:
            ticker_info = self.binance_client.get_symbol_ticker(symbol=market_symbol)
            preco_atual_fechamento = float(ticker_info['price'])
            
            drop_percentage = ((preco_atual_fechamento - self.preco_compra_ativo) / self.preco_compra_ativo) * 100
            
            self._desbloquear_saldo(market_symbol)
            saldo_livre = self._get_balance(self.moeda_atual_operacao, free_only=True)
            ignore_tick, step_size_value = self.get_precision_filters(market_symbol)
            
            self.binance_client.create_order(
                symbol=market_symbol, 
                side=SIDE_SELL, 
                type=ORDER_TYPE_MARKET, 
                quantity=self.format_decimal(saldo_livre, step_size_value)
            )
            
            if drop_percentage > 0:
                self.trades_won += 1
                motivo_log = f"VENDA_MANUAL (GAIN: {drop_percentage:+.2f}%)"
            else:
                self.trades_lost += 1
                motivo_log = f"VENDA_MANUAL (LOSS: {drop_percentage:+.2f}%)"
                
            self.lucro_diario_pct += drop_percentage
            self.trades_no_dia += 1
            
            self.historico_diario.append({
                "hora": datetime.now().strftime("%H:%M:%S"),
                "moeda": self.moeda_atual_operacao,
                "resultado": f"{drop_percentage:+.2f}%",
                "motivo": motivo_log
            })
            
            self.system_logger.info(f"✅ Venda Forçada concluída com sucesso! P/L da operação: {drop_percentage:+.2f}%")
            self.system_logger.info("⏱️ Motor em cooldown de 60 segundos antes de retomar as análises.")
            
            self.em_operacao = False
            self.moeda_atual_operacao = None
            self.stop_loss_monitor_drop = 0.0
            self.preco_compra_ativo = 0.0
            self.preco_atual_ativo = 0.0
            self.preco_alvo_ativo = 0.0
            self.quantidade_altcoin_ativa = 0.0
            self.peak_profit_percentage = 0.0
            self.chart_data_cache = []
            self.stop_loss_dinamico_ativo = 0.0
            
            self.ai_cooldown_until = time.time() + 60
            self._save_state()
            self._write_json_ui()

        except Exception as erro_venda:
            self.system_logger.error(f"❌ ERRO CRÍTICO na Venda Manual: {erro_venda}")

    def initialize(self):
        self.system_logger.info("🚀 Inicializando Profit Gain Pro V3.3.0 (Manual Override & Panic Button)")
        self._write_json_ui()

    def scout(self):
        self._check_ui_flags()
        self._check_daily_reset()
        self.system_logger.info(f"[HEARTBEAT] 💓 Motor executando varredura. Base oficial: {self.base_coin}")
        self.scan_market()
        self._write_json_ui()

    def update_values(self):
        self._check_ui_flags()
        self._check_daily_reset()
        self._write_json_ui()

    def _desbloquear_saldo(self, target_symbol):
        try:
            open_orders_list = self.binance_client.get_open_orders(symbol=target_symbol)
            for order_info in open_orders_list:
                self.system_logger.info(f"🚜 Trator: Cancelando ordem ({order_info['orderId']})...")
                self.binance_client.cancel_order(symbol=target_symbol, orderId=order_info['orderId'])
                time.sleep(0.5) 
        except Exception as erro_desbloqueio:
            self.system_logger.error(f"Erro ao limpar ordens travadas: {erro_desbloqueio}")

    def _get_balance(self, asset_symbol, free_only=False):
        try:
            balance_data = self.binance_client.get_asset_balance(asset=asset_symbol)
            if free_only:
                return float(balance_data['free'])
            return float(balance_data['free']) + float(balance_data['locked'])
        except Exception as e:
            self.system_logger.error(f"⚠️ Timeout de rede ao buscar saldo de {asset_symbol}: {e}")
            return -1.0

    def _recuperar_dados_compra_real(self, market_symbol):
        try:
            trades_recentes = self.binance_client.get_my_trades(symbol=market_symbol, limit=5)
            if trades_recentes:
                ultimo_trade = trades_recentes[-1]
                if ultimo_trade['isBuyer']:
                    preco_real = float(ultimo_trade['price'])
                    tempo_real = int(ultimo_trade['time']) / 1000.0
                    return preco_real, tempo_real
        except Exception as erro_historico:
            self.system_logger.error(f"Erro ao buscar histórico: {erro_historico}")
        return 0.0, 0.0

    def get_precision_filters(self, target_symbol):
        try:
            symbol_info = self.binance_client.get_symbol_info(target_symbol)
            tick_size_value, step_size_value = 0.00000001, 0.00000001
            for filter_item in symbol_info['filters']:
                if filter_item['filterType'] == 'PRICE_FILTER': tick_size_value = float(filter_item['tickSize'])
                if filter_item['filterType'] == 'LOT_SIZE': step_size_value = float(filter_item['stepSize'])
            return tick_size_value, step_size_value
        except Exception:
            return 0.0001, 0.0001

    def format_decimal(self, raw_value, step_size_value):
        precision_level = max(0, int(round(-math.log10(float(step_size_value)))))
        precision_factor = 10 ** precision_level
        truncated_value = math.floor(float(raw_value) * precision_factor) / precision_factor
        if precision_level == 0: return str(int(truncated_value))
        return f"{truncated_value:.{precision_level}f}"

    def get_enriched_data(self, target_symbol):
        try:
            klines_4h = self.binance_client.get_klines(symbol=target_symbol, interval='4h', limit=30)
            df_4h = pandas.DataFrame(klines_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'trades', 'tbbav', 'tbqav', 'ignore'])
            for col in ['close']: df_4h[col] = pandas.to_numeric(df_4h[col])
            df_4h.ta.rsi(length=14, append=True)
            
            klines_1h = self.binance_client.get_klines(symbol=target_symbol, interval='1h', limit=60)
            df_1h = pandas.DataFrame(klines_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'trades', 'tbbav', 'tbqav', 'ignore'])
            for col in ['open', 'high', 'low', 'close', 'vol']: df_1h[col] = pandas.to_numeric(df_1h[col])
            df_1h.ta.ema(length=21, append=True)
            df_1h.ta.rsi(length=14, append=True)
            df_1h.ta.atr(length=14, append=True) 
            
            klines_15m = self.binance_client.get_klines(symbol=target_symbol, interval='15m', limit=60)
            df_15m = pandas.DataFrame(klines_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'trades', 'tbbav', 'tbqav', 'ignore'])
            for col in ['open', 'high', 'low', 'close', 'vol']: df_15m[col] = pandas.to_numeric(df_15m[col])
            df_15m.ta.macd(fast=12, slow=26, signal=9, append=True)
            df_15m.ta.rsi(length=14, append=True)
            
            ultima_linha_4h = df_4h.iloc[-1]
            ultima_linha_1h = df_1h.iloc[-1]
            ultima_linha_15m = df_15m.iloc[-1]
            
            preco_atual = float(ultima_linha_1h['close'])
            
            rsi_4h = float(ultima_linha_4h.get('RSI_14', 50.0))
            rsi_1h = float(ultima_linha_1h.get('RSI_14', 50.0))
            rsi_15m = float(ultima_linha_15m.get('RSI_14', 50.0))
            if pandas.isna(rsi_4h): rsi_4h = 50.0
            if pandas.isna(rsi_1h): rsi_1h = 50.0
            if pandas.isna(rsi_15m): rsi_15m = 50.0
            
            macd_hist_15m = float(ultima_linha_15m.get('MACDh_12_26_9', 0.0))
            macd_histograma_15m_positivo = bool(macd_hist_15m > 0)
            
            ema21_1h = float(ultima_linha_1h.get('EMA_21', 0.0))
            atr_1h = float(ultima_linha_1h.get('ATRr_14', 0.0))
            
            micro_candle_fecha_em_alta = bool(ultima_linha_15m['close'] > ultima_linha_15m['open'])
            maxima_recente = float(df_1h['high'].tail(24).max())
            queda_da_maxima_pct = ((maxima_recente - preco_atual) / maxima_recente) * 100 if maxima_recente > 0 else 0.0
            
            try:
                media_volume_10_candles = df_15m['vol'].tail(11).head(10).mean()
                volume_candle_atual = df_15m['vol'].iloc[-1]
                volume_15m_acima_media = bool(volume_candle_atual > media_volume_10_candles)
            except Exception:
                volume_15m_acima_media = False

            distancia_ema21_1h_pct = ((preco_atual - ema21_1h) / ema21_1h) * 100 if ema21_1h > 0 else 0.0
            
            atr_pct_atual = (atr_1h / preco_atual) * 100 if preco_atual > 0 else 0.0
            fundo_exigido_atr_pct = -(atr_pct_atual * 2.0)
            
            try:
                ticker_info = self.binance_client.get_ticker(symbol=target_symbol)
                variacao_24h = float(ticker_info['priceChangePercent'])
                open_price = float(ticker_info['openPrice'])
                low_price = float(ticker_info['lowPrice'])
                variacao_24h_minima = ((low_price - open_price) / open_price) * 100 if open_price > 0 else 0.0
                volume_24h_usdt = float(ticker_info.get('quoteVolume', 0.0)) 
            except Exception:
                variacao_24h = 0.0
                variacao_24h_minima = 0.0
                volume_24h_usdt = 0.0

            stop_dinamico = atr_pct_atual * 2.0
            stop_dinamico = max(2.0, min(stop_dinamico, 3.50)) 
            
            dados_montados = {
                "moeda": target_symbol.replace(self.base_coin, ""),
                "preco_atual": preco_atual,
                "rsi_MACRO_4h": round(rsi_4h, 2),
                "rsi_INTER_1h": round(rsi_1h, 2),
                "rsi_MICRO_15m": round(rsi_15m, 2), 
                "macd_histograma_15m_positivo": macd_histograma_15m_positivo,
                "variacao_24h_pct": f"{variacao_24h:+.2f}%",
                "variacao_minima_24h_pct": f"{variacao_24h_minima:+.2f}%",
                "fundo_exigido_atr_pct": f"{fundo_exigido_atr_pct:+.2f}%",
                "micro_candle_confirmacao_alta": micro_candle_fecha_em_alta,
                "volume_24h_usdt": round(volume_24h_usdt, 2),
                "volume_15m_acima_media": volume_15m_acima_media,
                "distancia_ema21_1h_pct": f"{distancia_ema21_1h_pct:+.2f}%",
                "sugestao_stop_loss_atr": round(stop_dinamico, 2)
            }
            
            is_uptrend = preco_atual > ema21_1h
            return dados_montados, is_uptrend
        except Exception as erro:
            self.system_logger.error(f"Erro ao enriquecer dados de {target_symbol}: {erro}")
            return None, False

    def execute_real_trade(self, coin_symbol, preco_atual, stop_calculado_atr):
        market_symbol = f"{coin_symbol}{self.base_coin}"
        saldo_base_disponivel = self._get_balance(self.base_coin)
        
        if saldo_base_disponivel < 6.0: return False

        try:
            self.system_logger.info(f"🚀 ENTRADA REAL: Comprando {market_symbol} a mercado...")
            ignore_tick, step_size_value = self.get_precision_filters(market_symbol)
            
            compra_quantidade_usdt = saldo_base_disponivel * 0.99 
            quote_quantity_string = self.format_decimal(compra_quantidade_usdt, 0.01) 
            
            self.binance_client.create_order(symbol=market_symbol, side=SIDE_BUY, type=ORDER_TYPE_MARKET, quoteOrderQty=quote_quantity_string)
            time.sleep(2) 
            
            saldo_moeda_comprada = self._get_balance(coin_symbol)
            quantidade_vender_string = self.format_decimal(saldo_moeda_comprada, step_size_value)
            
            if float(quantidade_vender_string) == 0: return True

            self.system_logger.info(f"✅ Compra confirmada! Armando Trailing Stop invisível (+{self.trailing_activation_percentage:.2f}%) | Stop Tolerante: -{stop_calculado_atr:.2f}%")
            
            self.operation_start_time = time.time()
            self.quantidade_altcoin_ativa = float(quantidade_vender_string)
            self.preco_compra_ativo = float(preco_atual)
            self.peak_profit_percentage = 0.0
            self.preco_alvo_ativo = float(preco_atual) * (1 + (self.trailing_activation_percentage / 100))
            self.stop_loss_dinamico_ativo = float(stop_calculado_atr)
            self.last_switch_time = time.time()
            self._save_state()
            
            self.preco_atual_ativo = float(preco_atual)
            self.tempo_operacao_string = "0h 0m"
            self._write_json_ui() 
            
            return True

        except Exception as erro_compra:
            self.system_logger.error(f"❌ ERRO CRÍTICO na corretora: {erro_compra}")
            return False

    def _imprimir_parecer_ia(self, resumo_texto):
        linhas = str(resumo_texto).split('\n')
        if not linhas: return
        self.system_logger.info(f"🧠 Parecer da IA    : {linhas[0].strip()}")
        for linha in linhas[1:]:
            if linha.strip():
                self.system_logger.info(f"                      {linha.strip()}")

    def scan_market(self):
        if not self.em_operacao:
            if self.lucro_diario_pct >= 2.0 or self.trades_no_dia >= self.max_trades_diario:
                agora = datetime.now()
                amanha = agora + timedelta(days=1)
                meia_noite = datetime(amanha.year, amanha.month, amanha.day, 0, 0, 0)
                segundos_ate_meia_noite = (meia_noite - agora).total_seconds()
                
                self.system_logger.warning(f"🏆 META BATIDA OU LIMITE DE TRADES! Lucro: +{self.lucro_diario_pct:.2f}% | Trades: {self.trades_no_dia}/{self.max_trades_diario}")
                self.system_logger.info("💤 Bot entrando em hibernação institucional.")
                self.ai_cooldown_until = time.time() + segundos_ate_meia_noite
                return

        aptas_temporary_list = []
        geladeira_temporary_list = []
        lote_dados_ia = []
        
        try:
            account_data = self.binance_client.get_account()
            saldos_dicionario = {balance_info['asset']: float(balance_info['free']) + float(balance_info['locked']) for balance_info in account_data['balances']}
        except Exception:
            saldos_dicionario = {}

        for check_coin in self.system_configuration.SUPPORTED_COIN_LIST:
            if check_coin == self.base_coin: continue
            
            market_symbol = f"{check_coin}{self.base_coin}"
            dados_enriquecidos, is_uptrend = self.get_enriched_data(market_symbol)
            if dados_enriquecidos:
                moeda_alin = f"{check_coin: <7}"
                texto_linha_lateral = f"💼 {moeda_alin}: ${dados_enriquecidos['preco_atual']:.4f} ({dados_enriquecidos['variacao_24h_pct']})"
                
                if is_uptrend: aptas_temporary_list.append(texto_linha_lateral)
                else: geladeira_temporary_list.append(texto_linha_lateral)

                try:
                    var_atual_float = float(str(dados_enriquecidos['variacao_24h_pct']).replace('%', '').replace('+', ''))
                    var_minima_float = float(str(dados_enriquecidos['variacao_minima_24h_pct']).replace('%', '').replace('+', ''))
                    fundo_exigido_float = float(str(dados_enriquecidos['fundo_exigido_atr_pct']).replace('%', '').replace('+', ''))
                    
                    if var_minima_float <= fundo_exigido_float and var_atual_float <= -0.50:
                        lote_dados_ia.append(dados_enriquecidos)
                except Exception:
                    pass

        self.aptas_cache = sorted(aptas_temporary_list)
        self.geladeira_cache = sorted(geladeira_temporary_list)

        if not self.em_operacao:
            self.preco_atual_ativo, self.preco_alvo_ativo = 0.0, 0.0
            self.chart_data_cache = []
            self.tempo_operacao_string = "0h 0m"
            saldo_moeda_base = saldos_dicionario.get(self.base_coin, 0.0)
            
            if saldo_moeda_base < 5.0:
                ordem_busca_moedas = ["BTC"] + [check_coin for check_coin in self.system_configuration.SUPPORTED_COIN_LIST if check_coin not in ["BTC", self.base_coin]]
                for check_coin in ordem_busca_moedas:
                    quantidade_moeda = saldos_dicionario.get(check_coin, 0.0)
                    if quantidade_moeda > 0:
                        try:
                            ticker_info = self.binance_client.get_symbol_ticker(symbol=f"{check_coin}{self.base_coin}")
                            valor_convertido_dolar = quantidade_moeda * float(ticker_info['price'])
                            if valor_convertido_dolar >= 5.0:
                                self.system_logger.info(f"🔄 Recuperação de Estado: Assumindo {check_coin}.")
                                self.em_operacao = True
                                self.moeda_atual_operacao = check_coin
                                self.quantidade_altcoin_ativa = quantidade_moeda
                                if getattr(self, 'operation_start_time', 0.0) == 0.0:
                                    self.operation_start_time = time.time()
                                    self.last_switch_time = time.time()
                                self._save_state()
                                break
                        except Exception: pass

        if self.em_operacao:
            market_symbol = f"{self.moeda_atual_operacao}{self.base_coin}"
            
            try:
                klines_history = self.binance_client.get_klines(symbol=market_symbol, interval='15m', limit=30)
                self.chart_data_cache = [float(kline_item[4]) for kline_item in klines_history]
            except Exception: pass

            try:
                ticker_info = self.binance_client.get_symbol_ticker(symbol=market_symbol)
                self.preco_atual_ativo = float(ticker_info['price'])
                
                saldo_moeda_operada = self._get_balance(self.moeda_atual_operacao)

                if saldo_moeda_operada < 0:
                    return 

                if (saldo_moeda_operada * self.preco_atual_ativo) < 5.0:
                    self.system_logger.info(f"✅ Saldo esgotado em {self.moeda_atual_operacao}. Operação finalizada.")
                    self.em_operacao = False
                    self.moeda_atual_operacao = None
                    self.stop_loss_monitor_drop, self.preco_compra_ativo, self.preco_atual_ativo, self.preco_alvo_ativo, self.quantidade_altcoin_ativa, self.peak_profit_percentage = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                    self.chart_data_cache = []
                    self.stop_loss_dinamico_ativo = 0.0
                    self._save_state()
                    return

                if self.preco_compra_ativo <= 0:
                    preco_real, tempo_real = self._recuperar_dados_compra_real(market_symbol)
                    if preco_real > 0:
                        self.preco_compra_ativo = preco_real
                        if getattr(self, 'operation_start_time', 0) <= 0:
                            self.operation_start_time = tempo_real
                            self.last_switch_time = time.time()
                    else:
                        self.preco_compra_ativo = self.preco_atual_ativo
                    self._save_state()

                drop_percentage = ((self.preco_atual_ativo - self.preco_compra_ativo) / self.preco_compra_ativo) * 100
                self.stop_loss_monitor_drop = drop_percentage
                
                if drop_percentage > self.peak_profit_percentage:
                    self.peak_profit_percentage = drop_percentage
                    self._save_state()

                if self.peak_profit_percentage >= self.trailing_activation_percentage:
                    gatilho_venda_percentage = self.peak_profit_percentage - self.trailing_drop_percentage
                    self.preco_alvo_ativo = self.preco_compra_ativo * (1 + (gatilho_venda_percentage / 100))
                else:
                    self.preco_alvo_ativo = self.preco_compra_ativo * (1 + (self.trailing_activation_percentage / 100))

                segundos_ativos_operacao = time.time() - self.operation_start_time
                horas_ativas = int(segundos_ativos_operacao // 3600)
                minutos_ativos = int((segundos_ativos_operacao % 3600) // 60)
                tempo_preso_horas = segundos_ativos_operacao / 3600.0
                
                segundos_desde_switch_regra = time.time() - self.last_switch_time
                cooldown_restante_segundos = self.golden_rule_cooldown_seconds - segundos_desde_switch_regra
                status_cooldown_string = f" (Tribunal: {int(cooldown_restante_segundos//3600)}h {int((cooldown_restante_segundos%3600)//60)}m)" if cooldown_restante_segundos > 0 else " (Tribunal: Pronta)"
                self.tempo_operacao_string = f"{horas_ativas}h {minutos_ativos}m{status_cooldown_string}"

                is_selling_now = False
                motivo_venda_executada = ""
                
                stop_loss_atual = self.stop_loss_dinamico_ativo if self.stop_loss_dinamico_ativo > 0 else self.stop_loss_percentage_base

                if drop_percentage <= -10.0:
                    is_selling_now = True
                    motivo_venda_executada = "STOP_DESASTRE"
                    self.system_logger.warning(f"🚨 DESASTRE ABSOLUTO ACIONADO! Moeda perdeu 10% de valor. Cortando na carne.")
                elif drop_percentage <= -stop_loss_atual:
                    is_selling_now = True
                    motivo_venda_executada = "STOP_LOSS_DINAMICO"
                    self.system_logger.warning(f"🚨 STOP LOSS DINÂMICO (LIMITE) ACIONADO para {self.moeda_atual_operacao}! Queda de {drop_percentage:.2f}%")
                
                elif self.peak_profit_percentage >= self.trailing_activation_percentage and (self.peak_profit_percentage - drop_percentage) >= self.trailing_drop_percentage:
                    is_selling_now = True
                    motivo_venda_executada = "TAKE_PROFIT"
                    self.system_logger.info(f"✅ TAKE PROFIT TRAILING ACIONADO for {self.moeda_atual_operacao}! Pico: {self.peak_profit_percentage:.2f}% | Fechado em: {drop_percentage:.2f}%")

                if is_selling_now:
                    self._desbloquear_saldo(market_symbol) 
                    saldo_livre_disponivel = self._get_balance(self.moeda_atual_operacao, free_only=True)
                    ignore_tick, step_size_value = self.get_precision_filters(market_symbol)
                    
                    self.binance_client.create_order(symbol=market_symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=self.format_decimal(saldo_livre_disponivel, step_size_value))
                    
                    if "STOP" in motivo_venda_executada: 
                        self.trades_lost += 1
                    else: 
                        self.trades_won += 1
                    
                    self.lucro_diario_pct += drop_percentage
                    self.trades_no_dia += 1
                    
                    self.historico_diario.append({
                        "hora": datetime.now().strftime("%H:%M:%S"),
                        "moeda": self.moeda_atual_operacao,
                        "resultado": f"{drop_percentage:+.2f}%",
                        "motivo": motivo_venda_executada
                    })
                    
                    self.em_operacao = False
                    self.moeda_atual_operacao = None
                    self.stop_loss_monitor_drop, self.preco_compra_ativo, self.preco_atual_ativo, self.preco_alvo_ativo, self.quantidade_altcoin_ativa, self.peak_profit_percentage = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                    self.chart_data_cache = []
                    self.stop_loss_dinamico_ativo = 0.0
                    self._save_state()
                else:
                    if drop_percentage < -0.15 and cooldown_restante_segundos <= 0:
                        
                        if drop_percentage < -2.50:
                            self.system_logger.info(f"🛡️ TRIBUNAL BLOQUEADO no código Python: Prejuízo atual ({drop_percentage:.2f}%) excede o limite de -2.50%. HOLD obrigatório até recuperar.")
                            self.last_switch_time = time.time()
                            self._save_state()
                        else:
                            self.system_logger.info("⚖️ O ativo está na zona de swap segura (>-2.50%). Convocando o TRIBUNAL DE SWAP da IA...")
                            
                            lote_dados_swap = []
                            for d in lote_dados_ia:
                                if d['moeda'] != self.moeda_atual_operacao:
                                    try:
                                        var_atual_str = str(d['variacao_24h_pct']).replace('%', '').replace('+', '')
                                        var_minima_str = str(d['variacao_minima_24h_pct']).replace('%', '').replace('+', '')
                                        fundo_exigido_str = str(d['fundo_exigido_atr_pct']).replace('%', '').replace('+', '')
                                        
                                        if float(var_minima_str) <= float(fundo_exigido_str) and float(var_atual_str) <= -0.50:
                                            lote_dados_swap.append(d)
                                    except Exception: pass
                            
                            if lote_dados_swap:
                                analise_swap = self.ai_agent.analisar_swap(lote_dados_swap, self.moeda_atual_operacao, drop_percentage, tempo_preso_horas)
                                nova_moeda_promissora = analise_swap.get("moeda_vencedora", "HOLD")
                                confianca = analise_swap.get("confianca_final", 0)
                                resumo_decisao_swap = analise_swap.get("resumo_decisao", "Decisão mantida em HOLD.")
                                
                                if nova_moeda_promissora not in ["HOLD", "NENHUMA"] and confianca >= 95:
                                    item_escolhido = next((item for item in lote_dados_swap if item['moeda'] == nova_moeda_promissora), None)
                                    if item_escolhido:
                                        preco_alvo_swap = item_escolhido['preco_atual']
                                        stop_atr_swap = item_escolhido['sugestao_stop_loss_atr']
                                        
                                        self.system_logger.warning(f"👑 TRIBUNAL APROVOU SWAP! Assumindo prejuízo para migrar com {confianca}% de chance para {nova_moeda_promissora}!")
                                        
                                        self.relatorio_ia_completo = f"[{datetime.now().strftime('%H:%M:%S')}]\n\n⚖️ TRIBUNAL DE SWAP APROVADO\n🏆 Vencedora: {nova_moeda_promissora} ({confianca}%)\n\n🧠 Parecer:\n{resumo_decisao_swap}"
                                        self._imprimir_parecer_ia(resumo_decisao_swap)
                                        
                                        self._desbloquear_saldo(market_symbol) 
                                        saldo_livre_disponivel = self._get_balance(self.moeda_atual_operacao, free_only=True)
                                        ignore_tick, step_size_value = self.get_precision_filters(market_symbol)
                                        
                                        self.binance_client.create_order(symbol=market_symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=self.format_decimal(saldo_livre_disponivel, step_size_value))
                                        time.sleep(2)
                                        
                                        self.trades_lost += 1 
                                        self.lucro_diario_pct += drop_percentage 
                                        self.trades_no_dia += 1
                                        
                                        self.historico_diario.append({
                                            "hora": datetime.now().strftime("%H:%M:%S"),
                                            "moeda": self.moeda_atual_operacao,
                                            "resultado": f"{drop_percentage:+.2f}%",
                                            "motivo": "SWAP_IA_95%"
                                        })
                                        
                                        self.last_switch_time = time.time()
                                        self.em_operacao = False 
                                        self._save_state()
                                        
                                        if preco_alvo_swap > 0 and self.execute_real_trade(nova_moeda_promissora, preco_alvo_swap, stop_atr_swap):
                                            self.em_operacao = True
                                            self.moeda_atual_operacao = nova_moeda_promissora
                                    return
                                else:
                                    self.system_logger.info(f"🛡️ TRIBUNAL ORDENOU HOLD. O mercado não tem certeza de 95%+. Paciência com a moeda atual.")
                                    self.relatorio_ia_completo = f"[{datetime.now().strftime('%H:%M:%S')}]\n\n🛡️ TRIBUNAL DE SWAP RECUSADO (HOLD)\n⚖️ Veredito: Nenhuma moeda com 95%+ de chance detectada. Segurando {self.moeda_atual_operacao}.\n\n🧠 Parecer:\n{resumo_decisao_swap}"
                                    self._imprimir_parecer_ia(resumo_decisao_swap)
                                    self.last_switch_time = time.time() 
                                    self._save_state()

            except Exception as erro_monitoramento:
                self.system_logger.error(f"Erro no monitoramento: {erro_monitoramento}")

        else:
            tempo_atual = time.time()
            if tempo_atual < self.ai_cooldown_until:
                return

            if lote_dados_ia:
                self.system_logger.info(f"🟢 Submetendo Dossiê com {len(lote_dados_ia)} ativos ao Comitê IA...")
                analise_agente_ia = self.ai_agent.analisar_lote(lote_dados_ia)
                
                moeda_vencedora = analise_agente_ia.get("moeda_vencedora", "NENHUMA")
                confianca_final = analise_agente_ia.get("confianca_final", 0)
                resumo_decisao = analise_agente_ia.get("resumo_decisao", "Sem motivo específico.")

                self.system_logger.info("================ RELATÓRIO DA HORA ===================")
                self.system_logger.info(f"📋 Ativos Analisados : {len(lote_dados_ia)} moedas")
                self.system_logger.info(f"🏆 Vencedor Avaliado: {moeda_vencedora} (Confiança: {confianca_final}%)")
                self._imprimir_parecer_ia(resumo_decisao)
                self.system_logger.info("======================================================")

                self.relatorio_ia_completo = f"[{datetime.now().strftime('%H:%M:%S')}]\n\n🏆 Vencedora Avaliada: {moeda_vencedora} ({confianca_final}%)\n\n🧠 Parecer Detalhado Institucional:\n{resumo_decisao}"

                if moeda_vencedora != "NENHUMA" and confianca_final >= 90:
                    self.ultimo_veredito_ia = f"✅ COMPRA {moeda_vencedora} ({confianca_final}%): {resumo_decisao.splitlines()[0]}"
                    
                    item_escolhido = next((item for item in lote_dados_ia if item['moeda'] == moeda_vencedora), None)
                    if item_escolhido:
                        preco_alvo = item_escolhido['preco_atual']
                        stop_atr_alvo = item_escolhido['sugestao_stop_loss_atr']
                        
                        compra_realizada = self.execute_real_trade(moeda_vencedora, preco_alvo, stop_atr_alvo)
                        if compra_realizada:
                            self.em_operacao = True
                            self.moeda_atual_operacao = moeda_vencedora
                else:
                    primeira_linha = resumo_decisao.split('\n')[0] if resumo_decisao else "Sem motivo."
                    self.ultimo_veredito_ia = f"🛑 MERCADO VETADO: {primeira_linha}"
                    self.ai_cooldown_until = time.time() + 3600

    def _write_json_ui(self):
        try:
            btc_ticker_info = self.binance_client.get_ticker(symbol=f"BTC{self.base_coin}")
            btc_price_value = float(btc_ticker_info['lastPrice'])
            btc_change_value = float(btc_ticker_info['priceChangePercent'])
        except Exception:
            btc_price_value, btc_change_value = 0.0, 0.0
            
        texto_metas = f" | 📅 Diário: {self.lucro_diario_pct:+.2f}% ({self.trades_no_dia}/{self.max_trades_diario} Trades)"
        
        agora = time.time()
        if self.em_operacao:
            status_texto = "Em Operação (Alvo/Stop)"
        elif agora < self.ai_cooldown_until:
            status_texto = "Aguardando próxima análise"
        else:
            status_texto = "Mapeando Tendências"
        
        if self.em_operacao:
            stop_atual_exibir = self.stop_loss_dinamico_ativo if self.stop_loss_dinamico_ativo > 0 else self.stop_loss_percentage_base
            if self.peak_profit_percentage >= self.trailing_activation_percentage:
                detalhe_centralizado = f"[⏳] Duração: {self.tempo_operacao_string} | 🚀 TRAILING ATIVO! Pico: {self.peak_profit_percentage:.2f}% | Trava: {self.peak_profit_percentage - self.trailing_drop_percentage:.2f}%{texto_metas}"
            else:
                detalhe_centralizado = f"[⏳] Duração: {self.tempo_operacao_string} | [🎯] Gatilho Trailing: {self.trailing_activation_percentage:.2f}% | [🛑] SL: -{stop_atual_exibir:.2f}% (Var: {self.stop_loss_monitor_drop:+.2f}%){texto_metas}"
        else:
            if self.lucro_diario_pct >= 2.0 or self.trades_no_dia >= self.max_trades_diario:
                detalhe_centralizado = f"💤 HIBERNAÇÃO ATIVA: Metas ou limites atingidos. Retorno à meia-noite.{texto_metas}"
            else:
                detalhe_centralizado = f"🧠 ÚLTIMO VEREDITO: {self.ultimo_veredito_ia}{texto_metas}"
            
        status_data_dictionary = {
            "coin": self.moeda_atual_operacao if self.em_operacao else self.base_coin,
            "status": status_texto,
            "cooldown_until": self.ai_cooldown_until,
            "btc_price": btc_price_value,
            "btc_change": btc_change_value,
            "buy_price": self.preco_compra_ativo,
            "current_price": self.preco_atual_ativo,
            "target_price": self.preco_alvo_ativo,
            "active_qty": self.quantidade_altcoin_ativa,          
            "buy_time": self.operation_start_time,         
            "chart_data": self.chart_data_cache,
            "trades_won": self.trades_won,     
            "trades_lost": self.trades_lost,   
            "detalhe_atual": detalhe_centralizado,
            "aptas": self.aptas_cache,
            "geladeira": self.geladeira_cache,
            "trades_no_dia": self.trades_no_dia,
            "max_trades": self.max_trades_diario,
            "ai_report": self.relatorio_ia_completo,
            "daily_history": self.historico_diario
        }

        try:
            with open("bot_status.json", "w", encoding="utf-8") as file_handler: 
                json.dump(status_data_dictionary, file_handler, ensure_ascii=False, indent=2)
        except Exception:
            pass