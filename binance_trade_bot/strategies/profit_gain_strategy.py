import time
import json
import math
import os
import pandas
import pandas_ta

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
        self.ultimo_veredito_ia = "Aguardando sinal verde matemático..."
        
        self.taxa_maker = 0.10
        self.margem_poeira = 0.80
        self.lucro_liquido = 0.10 
        
        self.trailing_activation_percentage = self.taxa_maker * 2 + self.margem_poeira + self.lucro_liquido 
        self.trailing_drop_percentage = 0.20
        
        self.stop_loss_percentage = 2.0 
        self.stop_loss_monitor_drop = 0.0 
        self.maximum_hold_time_seconds = 3600      
        self.golden_rule_cooldown_seconds = 10800   
        
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
                    "peak_profit_percentage": self.peak_profit_percentage
                }, file_handler)
        except Exception as erro_escrita:
            self.system_logger.error(f"Erro ao salvar estado local: {erro_escrita}")

    def initialize(self):
        self.system_logger.info("🚀 Inicializando Profit Gain Pro com IA (MODO PRODUÇÃO)...")
        self._write_json_ui()

    def scout(self):
        self.system_logger.info(f"[HEARTBEAT] 💓 Motor executando varredura. Base oficial: {self.base_coin}")
        self.scan_market()
        self._write_json_ui()

    def update_values(self):
        self._write_json_ui()

    def _desbloquear_saldo(self, target_symbol):
        try:
            open_orders_list = self.binance_client.get_open_orders(symbol=target_symbol)
            for order_info in open_orders_list:
                self.system_logger.info(f"🚜 Trator: Cancelando ordem pendente antiga ({order_info['orderId']}) para liberar saldo...")
                self.binance_client.cancel_order(symbol=target_symbol, orderId=order_info['orderId'])
                time.sleep(0.5) 
        except Exception as erro_desbloqueio:
            self.system_logger.error(f"Erro ao tentar limpar ordens travadas: {erro_desbloqueio}")

    def _get_balance(self, asset_symbol, free_only=False):
        try:
            balance_data = self.binance_client.get_asset_balance(asset=asset_symbol)
            if free_only:
                return float(balance_data['free'])
            return float(balance_data['free']) + float(balance_data['locked'])
        except Exception:
            return 0.0

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

    def get_ema_signal(self, target_symbol):
        try:
            klines_data = self.binance_client.get_klines(symbol=target_symbol, interval='5m', limit=50)
            dataframe_klines = pandas.DataFrame(klines_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'trades', 'tbbav', 'tbqav', 'ignore'])
            
            column_names_to_convert = ['open', 'high', 'low', 'close', 'vol']
            for column_name in column_names_to_convert:
                dataframe_klines[column_name] = pandas.to_numeric(dataframe_klines[column_name])
            
            dataframe_klines.ta.ema(length=9, append=True)
            dataframe_klines.ta.ema(length=21, append=True)
            dataframe_klines.ta.rsi(length=14, append=True)
            
            preco_atual_fechamento = dataframe_klines['close'].iloc[-1]
            preco_fechamento_4h_atras = dataframe_klines['close'].iloc[0]
            variacao_percentual_4h = ((preco_atual_fechamento - preco_fechamento_4h_atras) / preco_fechamento_4h_atras) * 100 if preco_fechamento_4h_atras > 0 else 0.0
            
            ultima_linha_dataframe = dataframe_klines.iloc[-1]
            is_uptrend = ultima_linha_dataframe['EMA_9'] > ultima_linha_dataframe['EMA_21']
            rsi_atual = ultima_linha_dataframe['RSI_14'] if 'RSI_14' in dataframe_klines.columns else 50.0
            
            return is_uptrend, preco_atual_fechamento, variacao_percentual_4h, rsi_atual, dataframe_klines
        except Exception:
            return False, 0.0, 0.0, 50.0, None

    def execute_real_trade(self, coin_symbol, preco_atual):
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

            self.system_logger.info(f"✅ Compra confirmada! Armando Trailing Stop invisível (Gatilho em +{self.trailing_activation_percentage:.2f}%)")
            
            self.operation_start_time = time.time()
            self.quantidade_altcoin_ativa = float(quantidade_vender_string)
            self.preco_compra_ativo = float(preco_atual)
            self.peak_profit_percentage = 0.0
            self.preco_alvo_ativo = float(preco_atual) * (1 + (self.trailing_activation_percentage / 100))
            self._save_state()
            
            self.preco_atual_ativo = float(preco_atual)
            self.tempo_operacao_string = "0h 0m"
            self._write_json_ui() 
            
            return True

        except Exception as erro_compra:
            self.system_logger.error(f"❌ ERRO CRÍTICO na corretora: {erro_compra}")
            return False

    def scan_market(self):
        if not self.em_operacao:
            self.system_logger.info("📊 Mapeando gráficos e aguardando Validação da IA (Gemini)...")
            
        aptas_temporary_list = []
        geladeira_temporary_list = []
        
        try:
            account_data = self.binance_client.get_account()
            saldos_dicionario = {balance_info['asset']: float(balance_info['free']) + float(balance_info['locked']) for balance_info in account_data['balances']}
        except Exception:
            saldos_dicionario = {}

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
                                self.system_logger.info(f"🔄 Recuperação: Assumindo {check_coin} com Trailing Dinâmico.")
                                self.em_operacao = True
                                self.moeda_atual_operacao = check_coin
                                self.quantidade_altcoin_ativa = quantidade_moeda
                                if self.operation_start_time == 0.0:
                                    self.operation_start_time = time.time()
                                self._save_state()
                                break
                        except: pass

        if self.em_operacao:
            market_symbol = f"{self.moeda_atual_operacao}{self.base_coin}"
            
            try:
                klines_history = self.binance_client.get_klines(symbol=market_symbol, interval='5m', limit=30)
                self.chart_data_cache = [float(kline_item[4]) for kline_item in klines_history]
            except: pass

            try:
                ticker_info = self.binance_client.get_symbol_ticker(symbol=market_symbol)
                self.preco_atual_ativo = float(ticker_info['price'])
                
                saldo_moeda_operada = self._get_balance(self.moeda_atual_operacao)
                if (saldo_moeda_operada * self.preco_atual_ativo) < 5.0:
                    self.system_logger.info(f"✅ Saldo esgotado em {self.moeda_atual_operacao}. Operação finalizada.")
                    self.em_operacao = False
                    self.moeda_atual_operacao = None
                    self.stop_loss_monitor_drop, self.preco_compra_ativo, self.preco_atual_ativo, self.preco_alvo_ativo, self.quantidade_altcoin_ativa, self.peak_profit_percentage = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                    self.chart_data_cache = []
                    self._save_state()
                    return

                if self.preco_compra_ativo <= 0:
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
                
                segundos_desde_switch_regra = time.time() - self.last_switch_time
                cooldown_restante_segundos = self.golden_rule_cooldown_seconds - segundos_desde_switch_regra
                status_cooldown_string = f" (Regra de Ouro em: {int(cooldown_restante_segundos//3600)}h {int((cooldown_restante_segundos%3600)//60)}m)" if cooldown_restante_segundos > 0 else " (Regra de Ouro: Pronta)"
                self.tempo_operacao_string = f"{horas_ativas}h {minutos_ativos}m{status_cooldown_string}"

                is_selling_now = False
                motivo_venda_executada = ""

                if drop_percentage <= -self.stop_loss_percentage:
                    is_selling_now = True
                    motivo_venda_executada = "STOP_LOSS"
                    self.system_logger.warning(f"🚨 STOP LOSS ACIONADO para {self.moeda_atual_operacao}! Queda de {drop_percentage:.2f}%")
                
                elif self.peak_profit_percentage >= self.trailing_activation_percentage and (self.peak_profit_percentage - drop_percentage) >= self.trailing_drop_percentage:
                    is_selling_now = True
                    motivo_venda_executada = "TRAILING_STOP"
                    self.system_logger.info(f"✅ TAKE PROFIT TRAILING ACIONADO para {self.moeda_atual_operacao}! Pico atingido: {self.peak_profit_percentage:.2f}% | Fechando em: {drop_percentage:.2f}%")

                if is_selling_now:
                    self._desbloquear_saldo(market_symbol) 
                    saldo_livre_disponivel = self._get_balance(self.moeda_atual_operacao, free_only=True)
                    ignore_tick, step_size_value = self.get_precision_filters(market_symbol)
                    
                    self.binance_client.create_order(symbol=market_symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=self.format_decimal(saldo_livre_disponivel, step_size_value))
                    
                    if motivo_venda_executada == "STOP_LOSS": self.trades_lost += 1
                    else: self.trades_won += 1
                    
                    self.em_operacao = False
                    self.moeda_atual_operacao = None
                    self.stop_loss_monitor_drop, self.preco_compra_ativo, self.preco_atual_ativo, self.preco_alvo_ativo, self.quantidade_altcoin_ativa, self.peak_profit_percentage = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                    self.chart_data_cache = []
                    self._save_state()
                else:
                    if segundos_ativos_operacao > self.maximum_hold_time_seconds and (-1.0 <= drop_percentage <= -0.15) and cooldown_restante_segundos <= 0:
                        self.system_logger.info("⏳ Bot preso. Caçando nova oportunidade...")
                        nova_moeda_promissora = None
                        nova_cotacao_promissora = 0.0
                        
                        for check_coin in self.system_configuration.SUPPORTED_COIN_LIST:
                            if check_coin in [self.base_coin, self.moeda_atual_operacao]: continue
                            is_uptrend, preco_atual, variacao_4h, rsi_atual, dataframe_candles = self.get_ema_signal(f"{check_coin}{self.base_coin}")
                            
                            if is_uptrend and rsi_atual < 70.0:
                                self.system_logger.info(f"🔎 Regra de Ouro: Validando {check_coin} com a IA...")
                                analise_agente_ia = self.ai_agent.analisar(check_coin, preco_atual, rsi_atual, variacao_4h, dataframe_candles)
                                
                                if analise_agente_ia.get("recomendacao") == "COMPRAR" and analise_agente_ia.get("confianca", 0) >= 70:
                                    self.system_logger.warning(f"🤖 IA APROVOU TROCA ({analise_agente_ia.get('confianca')}%): {analise_agente_ia.get('motivo')}")
                                    nova_moeda_promissora = check_coin
                                    nova_cotacao_promissora = preco_atual
                                    break
                                else:
                                    self.system_logger.info(f"🛑 IA VETOU TROCA para {check_coin}: {analise_agente_ia.get('motivo')}")
                        
                        if nova_moeda_promissora:
                            self.system_logger.warning(f"👑 REGRA DE OURO! Migrando para {nova_moeda_promissora} com aval da IA!")
                            self._desbloquear_saldo(market_symbol) 
                            saldo_livre_disponivel = self._get_balance(self.moeda_atual_operacao, free_only=True)
                            ignore_tick, step_size_value = self.get_precision_filters(market_symbol)
                            
                            self.binance_client.create_order(symbol=market_symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=self.format_decimal(saldo_livre_disponivel, step_size_value))
                            time.sleep(2)
                            
                            self.trades_lost += 1 
                            self.last_switch_time = time.time()
                            self.em_operacao = False 
                            self._save_state()
                            
                            if self.execute_real_trade(nova_moeda_promissora, nova_cotacao_promissora):
                                self.em_operacao = True
                                self.moeda_atual_operacao = nova_moeda_promissora
                            return

                    self._write_json_ui() 
            except Exception as erro_monitoramento:
                self.system_logger.error(f"Erro no monitoramento: {erro_monitoramento}")

        # ---------------- VARREDURA GRÁFICA & ANÁLISE IA ----------------
        for check_coin in self.system_configuration.SUPPORTED_COIN_LIST:
            if check_coin == self.base_coin: continue
            market_symbol = f"{check_coin}{self.base_coin}"
            
            is_uptrend, preco_atual, variacao_4h, rsi_atual, dataframe_candles = self.get_ema_signal(market_symbol)
            texto_preco = f"${preco_atual:.4f}"
            texto_variacao = f"4H: {variacao_4h:+.2f}%"
            
            quantidade_moeda_carteira = saldos_dicionario.get(check_coin, 0.0)
            texto_linha_lateral = f"💼 {check_coin}: {texto_preco} ({texto_variacao})" if quantidade_moeda_carteira > 0.000001 else f"{check_coin}: {texto_preco} ({texto_variacao})"
            
            if is_uptrend:
                if rsi_atual >= 70.0:
                    geladeira_temporary_list.append(texto_linha_lateral)
                    if not self.em_operacao:
                        self.system_logger.info(f"⚠️ {check_coin} | Filtro Matemático: EMA cruzou, mas RSI estourado em {rsi_atual:.2f}. Evitando topo!")
                else:
                    aptas_temporary_list.append(texto_linha_lateral)
                    if not self.em_operacao:
                        self.system_logger.info(f"🟢 {check_coin} | Matemática OK (EMA Alta, RSI {rsi_atual:.2f}). Solicitando aval da IA...")
                        
                        analise_agente_ia = self.ai_agent.analisar(check_coin, preco_atual, rsi_atual, variacao_4h, dataframe_candles)

                        if analise_agente_ia.get("recomendacao") == "COMPRAR" and analise_agente_ia.get("confianca", 0) >= 70:
                            self.system_logger.warning(f"🤖 IA APROVOU ({analise_agente_ia.get('confianca')}%): {analise_agente_ia.get('motivo')}")
                            self.ultimo_veredito_ia = f"✅ COMPRA {check_coin} APROVADA ({analise_agente_ia.get('confianca')}%)"
                            
                            compra_realizada_com_sucesso = self.execute_real_trade(check_coin, preco_atual)
                            if compra_realizada_com_sucesso:
                                self.em_operacao = True
                                self.moeda_atual_operacao = check_coin
                        else:
                            motivo_recusa_texto = analise_agente_ia.get('motivo', 'Sem motivo detalhado')
                            veredito_texto = f"🛑 {check_coin} VETADA ({analise_agente_ia.get('confianca', 0)}%): {motivo_recusa_texto}"
                            self.system_logger.info(veredito_texto)
                            self.ultimo_veredito_ia = veredito_texto
                            
            else:
                geladeira_temporary_list.append(texto_linha_lateral)
                if not self.em_operacao:
                    if variacao_4h < -2.0:
                        self.system_logger.info(f"❄️ {check_coin} | Análise: Em geladeira. Ativo sangrando ({variacao_4h:.2f}% nas últimas 4h).")
                    else:
                        self.system_logger.info(f"⏸️ {check_coin} | Análise: Abaixo da curva (EMA 9 < 21).")

        self.aptas_cache = aptas_temporary_list
        self.geladeira_cache = geladeira_temporary_list

    def _write_json_ui(self):
        try:
            btc_ticker_info = self.binance_client.get_ticker(symbol=f"BTC{self.base_coin}")
            btc_price_value = float(btc_ticker_info['lastPrice'])
            btc_change_value = float(btc_ticker_info['priceChangePercent'])
        except Exception:
            btc_price_value, btc_change_value = 0.0, 0.0
            
        if self.em_operacao:
            if self.peak_profit_percentage >= self.trailing_activation_percentage:
                detalhe_centralizado = f"[⏳] Duração: {self.tempo_operacao_string} | 🚀 TRAILING ATIVO! Pico: {self.peak_profit_percentage:.2f}% | Trava de Venda: {self.peak_profit_percentage - self.trailing_drop_percentage:.2f}%"
            else:
                detalhe_centralizado = f"[⏳] Duração: {self.tempo_operacao_string} | [🎯] Gatilho Trailing: {self.trailing_activation_percentage:.2f}% | [🛑] SL: -{self.stop_loss_percentage:.2f}% (Var Atual: {self.stop_loss_monitor_drop:+.2f}%)"
        else:
            detalhe_centralizado = f"🧠 ÚLTIMO VEREDITO IA: {self.ultimo_veredito_ia}"
            
        status_data_dictionary = {
            "coin": self.moeda_atual_operacao if self.em_operacao else self.base_coin,
            "status": "Em Operação (Alvo/Stop)" if self.em_operacao else "Mapeando Tendências",
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
            "geladeira": self.geladeira_cache
        }

        try:
            with open("bot_status.json", "w", encoding="utf-8") as file_handler: 
                json.dump(status_data_dictionary, file_handler, ensure_ascii=False, indent=2)
        except Exception:
            pass