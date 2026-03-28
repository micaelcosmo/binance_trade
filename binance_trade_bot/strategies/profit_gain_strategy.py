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
        self.ultimo_veredito_ia = "Aguardando lote de dados..."
        self.ai_cooldown_until = 0.0
        
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
        self.system_logger.info("🚀 Inicializando Profit Gain Pro com IA...")
        self._write_json_ui()

    def scout(self):
        if os.path.exists("reset_trades.flag"):
            self.trades_won = 0
            self.trades_lost = 0
            self._save_state()
            try:
                os.remove("reset_trades.flag")
                self.system_logger.info("♻️ Placar de Trades zerado com sucesso!")
            except Exception:
                pass

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
            klines_data = self.binance_client.get_klines(symbol=target_symbol, interval='1h', limit=60)
            dataframe_klines = pandas.DataFrame(klines_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'trades', 'tbbav', 'tbqav', 'ignore'])
            
            column_names_to_convert = ['open', 'high', 'low', 'close', 'vol']
            for column_name in column_names_to_convert:
                dataframe_klines[column_name] = pandas.to_numeric(dataframe_klines[column_name])
            
            dataframe_klines.ta.ema(length=9, append=True)
            dataframe_klines.ta.ema(length=21, append=True)
            dataframe_klines.ta.ema(length=50, append=True)
            dataframe_klines.ta.rsi(length=14, append=True)
            
            ultima_linha = dataframe_klines.iloc[-1]
            preco_atual = float(ultima_linha['close'])
            rsi_atual = float(ultima_linha.get('RSI_14', 50.0))
            ema9 = float(ultima_linha.get('EMA_9', 0.0))
            ema21 = float(ultima_linha.get('EMA_21', 0.0))
            
            if pandas.isna(rsi_atual): rsi_atual = 50.0
            if pandas.isna(ema9): ema9 = 0.0
            if pandas.isna(ema21): ema21 = 0.0
            
            try:
                ticker_info = self.binance_client.get_ticker(symbol=target_symbol)
                variacao_24h = float(ticker_info['priceChangePercent'])
                maxima_24h = float(ticker_info['highPrice'])
            except Exception:
                variacao_24h = 0.0
                maxima_24h = preco_atual

            distancia_max = ((preco_atual - maxima_24h) / maxima_24h) * 100 if maxima_24h > 0 else 0.0
            
            if preco_atual > ema9 and ema9 > ema21:
                status_emas = "Preço ACIMA da EMA 9 e 21 (Tendência de Alta)."
            elif preco_atual < ema21:
                status_emas = "Preço ABAIXO da EMA 21 (Tendência de Baixa)."
            else:
                status_emas = "Preço Consolidando entre EMA 9 e 21."
                
            try:
                vol_recente = dataframe_klines['vol'].iloc[-4:-1].mean()
                vol_passado = dataframe_klines['vol'].iloc[-7:-4].mean()
                tendencia_vol = "CRESCENTE" if vol_recente > vol_passado else "SECANDO"
            except Exception:
                tendencia_vol = "ESTÁVEL"
                
            is_uptrend = preco_atual > ema21
            
            dados_montados = {
                "moeda": target_symbol.replace(self.base_coin, ""),
                "preco_atual": preco_atual,
                "rsi_14_periodos": round(rsi_atual, 2),
                "status_emas": status_emas,
                "tendencia_volume": tendencia_vol,
                "variacao_24h_pct": f"{variacao_24h:+.2f}%",
                "distancia_maxima_24h": f"{distancia_max:+.2f}%"
            }
            return dados_montados, is_uptrend
        except Exception as erro:
            self.system_logger.error(f"Erro ao enriquecer dados de {target_symbol}: {erro}")
            return None, False

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
            self.system_logger.info("📊 Compilando Dossiê Quantitativo 1H...")
            
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
                                if getattr(self, 'operation_start_time', 0.0) == 0.0:
                                    self.operation_start_time = time.time()
                                self._save_state()
                                break
                        except Exception: pass

        if self.em_operacao:
            market_symbol = f"{self.moeda_atual_operacao}{self.base_coin}"
            
            try:
                klines_history = self.binance_client.get_klines(symbol=market_symbol, interval='5m', limit=30)
                self.chart_data_cache = [float(kline_item[4]) for kline_item in klines_history]
            except Exception: pass

            try:
                ticker_info = self.binance_client.get_symbol_ticker(symbol=market_symbol)
                self.preco_atual_ativo = float(ticker_info['price'])
                
                saldo_moeda_operada = self._get_balance(self.moeda_atual_operacao)

                if saldo_moeda_operada < 0:
                    self.system_logger.warning("⏳ Conexão perdida: Congelando estado da operação até a internet voltar...")
                    return 

                if (saldo_moeda_operada * self.preco_atual_ativo) < 5.0:
                    self.system_logger.info(f"✅ Saldo esgotado em {self.moeda_atual_operacao}. Operação finalizada.")
                    self.em_operacao = False
                    self.moeda_atual_operacao = None
                    self.stop_loss_monitor_drop, self.preco_compra_ativo, self.preco_atual_ativo, self.preco_alvo_ativo, self.quantidade_altcoin_ativa, self.peak_profit_percentage = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                    self.chart_data_cache = []
                    self._save_state()
                    return

                if self.preco_compra_ativo <= 0:
                    preco_real, tempo_real = self._recuperar_dados_compra_real(market_symbol)
                    
                    if preco_real > 0:
                        self.preco_compra_ativo = preco_real
                        if getattr(self, 'operation_start_time', 0) <= 0:
                            self.operation_start_time = tempo_real
                        self.system_logger.warning(f"✅ Memória Restaurada! Preço real de compra: ${preco_real:.6f}")
                    else:
                        self.preco_compra_ativo = self.preco_atual_ativo
                        self.system_logger.warning("⚠️ Histórico não encontrado. Assumindo preço atual.")
                        
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
                status_cooldown_string = f" (Ouro: {int(cooldown_restante_segundos//3600)}h {int((cooldown_restante_segundos%3600)//60)}m)" if cooldown_restante_segundos > 0 else " (Ouro: Pronta)"
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
                        self.system_logger.info("⏳ Bot preso. Regra de Ouro: Coletando lote para Swap...")
                        lote_dados_swap = []
                        
                        for check_coin in self.system_configuration.SUPPORTED_COIN_LIST:
                            if check_coin in [self.base_coin, self.moeda_atual_operacao]: continue
                            dados_swap, is_uptrend_swap = self.get_enriched_data(f"{check_coin}{self.base_coin}")
                            
                            if dados_swap and dados_swap['rsi_14_periodos'] < 75.0:
                                lote_dados_swap.append(dados_swap)
                                
                        if lote_dados_swap:
                            self.system_logger.info(f"🔎 Submetendo {len(lote_dados_swap)} opções ao Comitê IA...")
                            analise_agente_ia = self.ai_agent.analisar_lote(lote_dados_swap)
                            nova_moeda_promissora = analise_agente_ia.get("moeda_vencedora", "NENHUMA")
                            confianca = analise_agente_ia.get("confianca_setup", 0)
                            
                            if nova_moeda_promissora != "NENHUMA" and confianca >= 70:
                                preco_alvo_swap = next((item['preco_atual'] for item in lote_dados_swap if item['moeda'] == nova_moeda_promissora), 0.0)
                                self.system_logger.warning(f"👑 REGRA DE OURO! Migrando para {nova_moeda_promissora} com aval da IA! Motivo: {analise_agente_ia.get('motivo_investimento')}")
                                
                                self._desbloquear_saldo(market_symbol) 
                                saldo_livre_disponivel = self._get_balance(self.moeda_atual_operacao, free_only=True)
                                ignore_tick, step_size_value = self.get_precision_filters(market_symbol)
                                
                                self.binance_client.create_order(symbol=market_symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=self.format_decimal(saldo_livre_disponivel, step_size_value))
                                time.sleep(2)
                                
                                self.trades_lost += 1 
                                self.last_switch_time = time.time()
                                self.em_operacao = False 
                                self._save_state()
                                
                                if preco_alvo_swap > 0 and self.execute_real_trade(nova_moeda_promissora, preco_alvo_swap):
                                    self.em_operacao = True
                                    self.moeda_atual_operacao = nova_moeda_promissora
                                return

                self._write_json_ui() 
            except Exception as erro_monitoramento:
                self.system_logger.error(f"Erro no monitoramento: {erro_monitoramento}")

        if not self.em_operacao:
            tempo_atual = time.time()
            if tempo_atual < self.ai_cooldown_until:
                minutos_restantes = int((self.ai_cooldown_until - tempo_atual) / 60)
                self.system_logger.info(f"⏳ IA em Cooldown de Proteção. Aguardando {minutos_restantes}m para próxima varredura...")
                return

            lote_dados_ia = []
            
            for check_coin in self.system_configuration.SUPPORTED_COIN_LIST:
                if check_coin == self.base_coin: continue
                market_symbol = f"{check_coin}{self.base_coin}"
                
                dados_enriquecidos, is_uptrend = self.get_enriched_data(market_symbol)
                
                if dados_enriquecidos:
                    moeda_alin = f"{check_coin: <7}"
                    texto_linha_lateral = f"💼 {moeda_alin}: ${dados_enriquecidos['preco_atual']:.4f} ({dados_enriquecidos['variacao_24h_pct']})"
                    
                    lote_dados_ia.append(dados_enriquecidos)

                    if is_uptrend:
                        aptas_temporary_list.append(texto_linha_lateral)
                    else:
                        geladeira_temporary_list.append(texto_linha_lateral)

            # Ordenação alfabética para facilitar a leitura visual no painel
            self.aptas_cache = sorted(aptas_temporary_list)
            self.geladeira_cache = sorted(geladeira_temporary_list)

            if lote_dados_ia:
                self.system_logger.info(f"🟢 Submetendo Dossiê completo com {len(lote_dados_ia)} ativos ao Comitê Quantitativo IA...")
                analise_agente_ia = self.ai_agent.analisar_lote(lote_dados_ia)
                
                moeda_vencedora = analise_agente_ia.get("moeda_vencedora", "NENHUMA")
                confianca_setup = analise_agente_ia.get("confianca_setup", 0)
                motivo_investimento = analise_agente_ia.get("motivo_investimento", "Sem motivo específico.")

                if moeda_vencedora != "NENHUMA" and confianca_setup >= 70:
                    self.system_logger.warning(f"🤖 IA ESCOLHEU A CAMPEÃ DA RODADA ({confianca_setup}% de Confiança)!")
                    self.system_logger.warning(f"🎯 SÍMBOLO: {moeda_vencedora} | TESE: {motivo_investimento}")
                    
                    self.ultimo_veredito_ia = f"✅ COMPRA {moeda_vencedora} ({confianca_setup}%): {motivo_investimento}"
                    
                    preco_alvo = next((item['preco_atual'] for item in lote_dados_ia if item['moeda'] == moeda_vencedora), 0.0)
                    if preco_alvo > 0:
                        compra_realizada = self.execute_real_trade(moeda_vencedora, preco_alvo)
                        if compra_realizada:
                            self.em_operacao = True
                            self.moeda_atual_operacao = moeda_vencedora
                else:
                    self.system_logger.info(f"🛑 IA VETOU O LOTE INTEIRO: {motivo_investimento}")
                    self.ultimo_veredito_ia = f"🛑 MERCADO VETADO: {motivo_investimento}"
                    self.system_logger.warning("⏳ Proteção Anti-Loss Ativada: Pausando a IA por 30 minutos.")
                    self.ai_cooldown_until = time.time() + 1800

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