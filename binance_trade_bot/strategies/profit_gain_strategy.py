import time
import json
import math
import os
import pandas as pd
import pandas_ta as ta
from binance.enums import *

class Strategy:
    def __init__(self, manager, db, logger, config):
        self.manager = manager
        self.db = db
        self.logger = logger
        self.config = config
        self.client = manager.binance_client
        
        bridge_attr = getattr(self.config, 'BRIDGE', 'USDT')
        self.base_coin = getattr(bridge_attr, 'symbol', bridge_attr)
        
        # --- MATEMÁTICA DA OPERAÇÃO (TRAILING STOP) ---
        self.taxa_maker = 0.10
        self.margem_poeira = 0.80
        self.lucro_liquido = 0.10 
        
        self.trailing_activation_perc = self.taxa_maker * 2 + self.margem_poeira + self.lucro_liquido 
        self.trailing_drop_perc = 0.20
        
        # 🛑 AIRBAG & REGRA DE OURO
        self.stop_loss_perc = 2.0 
        self.sl_monitor_drop = 0.0 
        self.max_hold_time_secs = 3600      
        self.golden_rule_cooldown = 10800   
        
        # --- ESTADOS (Persistidos no NoSQL/JSON) ---
        self.operation_start_time = 0.0
        self.last_switch_time = 0.0
        self.qtd_altcoin_ativa = 0.0  
        self.preco_compra_ativo = 0.0
        self.peak_profit_perc = 0.0   
        self.trades_won = 0           
        self.trades_lost = 0          
        self._load_state() 
        
        # --- ESTADOS PARA A UI ---
        self.preco_atual_ativo = 0.0
        self.preco_alvo_ativo = 0.0
        self.chart_data_cache = []
        self.tempo_operacao_str = "0h 0m"
        
        self.em_operacao = False
        self.moeda_atual_operacao = None
        self.aptas_cache = []
        self.geladeira_cache = []

    def _load_state(self):
        if os.path.exists("profit_gain_state.json"):
            try:
                with open("profit_gain_state.json", "r") as f:
                    data = json.load(f)
                    self.operation_start_time = data.get("operation_start_time", 0.0)
                    self.last_switch_time = data.get("last_switch_time", 0.0)
                    self.qtd_altcoin_ativa = data.get("qtd_altcoin_ativa", 0.0)
                    self.trades_won = data.get("trades_won", 0)
                    self.trades_lost = data.get("trades_lost", 0)
                    self.preco_compra_ativo = data.get("preco_compra_ativo", 0.0)
                    self.peak_profit_perc = data.get("peak_profit_perc", 0.0)
            except Exception:
                pass

    def _save_state(self):
        try:
            with open("profit_gain_state.json", "w") as f:
                json.dump({
                    "operation_start_time": self.operation_start_time,
                    "last_switch_time": self.last_switch_time,
                    "qtd_altcoin_ativa": self.qtd_altcoin_ativa,
                    "trades_won": self.trades_won,
                    "trades_lost": self.trades_lost,
                    "preco_compra_ativo": self.preco_compra_ativo,
                    "peak_profit_perc": self.peak_profit_perc
                }, f)
        except Exception as e:
            self.logger.error(f"Erro ao salvar estado local: {e}")

    def initialize(self):
        self.logger.info("🚀 Inicializando Profit Gain Pro (MODO PRODUÇÃO)...")
        self._write_json_ui()

    def scout(self):
        self.logger.info(f"[HEARTBEAT] 💓 Motor executando varredura. Base oficial: {self.base_coin}")
        self.scan_market()
        self._write_json_ui()

    def update_values(self):
        self._write_json_ui()

    def _get_balance(self, asset):
        try:
            b = self.client.get_asset_balance(asset=asset)
            return float(b['free']) + float(b['locked'])
        except Exception:
            return 0.0

    def get_precision_filters(self, symbol):
        try:
            info = self.client.get_symbol_info(symbol)
            tick_size, step_size = 0.00000001, 0.00000001
            for f in info['filters']:
                if f['filterType'] == 'PRICE_FILTER': tick_size = float(f['tickSize'])
                if f['filterType'] == 'LOT_SIZE': step_size = float(f['stepSize'])
            return tick_size, step_size
        except Exception:
            return 0.0001, 0.0001

    def format_decimal(self, value, step):
        precision = max(0, int(round(-math.log10(float(step)))))
        factor = 10 ** precision
        truncated = math.floor(float(value) * factor) / factor
        if precision == 0: return str(int(truncated))
        return f"{truncated:.{precision}f}"

    def get_ema_signal(self, symbol):
        try:
            klines = self.client.get_klines(symbol=symbol, interval='5m', limit=50)
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'trades', 'tbbav', 'tbqav', 'ignore'])
            df['close'] = pd.to_numeric(df['close'])
            df.ta.ema(length=9, append=True)
            df.ta.ema(length=21, append=True)
            
            preco_atual = df['close'].iloc[-1]
            preco_4h_atras = df['close'].iloc[0]
            var_4h = ((preco_atual - preco_4h_atras) / preco_4h_atras) * 100 if preco_4h_atras > 0 else 0.0
            
            ultima_linha = df.iloc[-1]
            uptrend = ultima_linha['EMA_9'] > ultima_linha['EMA_21']
            
            return uptrend, preco_atual, var_4h
        except Exception:
            return False, 0.0, 0.0

    def execute_real_trade(self, coin, preco_atual):
        symbol = f"{coin}{self.base_coin}"
        saldo_base = self._get_balance(self.base_coin)
        
        if saldo_base < 6.0: return False

        try:
            self.logger.info(f"🚀 ENTRADA REAL: Comprando {symbol} a mercado...")
            _, step_size = self.get_precision_filters(symbol)
            
            compra_usdt = saldo_base * 0.99 
            quote_qty_str = self.format_decimal(compra_usdt, 0.01) 
            
            self.client.create_order(symbol=symbol, side=SIDE_BUY, type=ORDER_TYPE_MARKET, quoteOrderQty=quote_qty_str)
            time.sleep(2) 
            
            saldo_moeda = self._get_balance(coin)
            qtd_vender_str = self.format_decimal(saldo_moeda, step_size)
            
            if float(qtd_vender_str) == 0: return True

            self.logger.info(f"✅ Compra confirmada! Armando Trailing Stop invisível (Gatilho em +{self.trailing_activation_perc:.2f}%)")
            
            self.operation_start_time = time.time()
            self.qtd_altcoin_ativa = float(qtd_vender_str)
            self.preco_compra_ativo = float(preco_atual)
            self.peak_profit_perc = 0.0
            self.preco_alvo_ativo = float(preco_atual) * (1 + (self.trailing_activation_perc / 100))
            self._save_state()
            
            self.preco_atual_ativo = float(preco_atual)
            self.tempo_operacao_str = "0h 0m"
            self._write_json_ui() 
            
            return True

        except Exception as e:
            self.logger.error(f"❌ ERRO CRÍTICO na corretora: {e}")
            return False

    def scan_market(self):
        if not self.em_operacao:
            self.logger.info("📊 Mapeando gráficos, rodando análise de ativos...")
            
        aptas_temp = []
        geladeira_temp = []
        
        try:
            acc = self.client.get_account()
            saldos = {b['asset']: float(b['free']) + float(b['locked']) for b in acc['balances']}
        except Exception:
            saldos = {}

        if not self.em_operacao:
            self.preco_atual_ativo, self.preco_alvo_ativo = 0.0, 0.0
            self.chart_data_cache = []
            self.tempo_operacao_str = "0h 0m"
            saldo_base = saldos.get(self.base_coin, 0.0)
            if saldo_base < 5.0:
                ordem_busca = ["BTC"] + [c for c in self.manager.config.SUPPORTED_COIN_LIST if c not in ["BTC", self.base_coin]]
                for c in ordem_busca:
                    qtd = saldos.get(c, 0.0)
                    if qtd > 0:
                        try:
                            ticker = self.client.get_symbol_ticker(symbol=f"{c}{self.base_coin}")
                            valor_dolar = qtd * float(ticker['price'])
                            if valor_dolar >= 5.0:
                                self.logger.info(f"🔄 Recuperação: Assumindo {c} com Trailing Dinâmico.")
                                self.em_operacao = True
                                self.moeda_atual_operacao = c
                                self.qtd_altcoin_ativa = qtd
                                if self.operation_start_time == 0.0:
                                    self.operation_start_time = time.time()
                                self._save_state()
                                break
                        except: pass

        if self.em_operacao:
            symbol = f"{self.moeda_atual_operacao}{self.base_coin}"
            
            try:
                kl = self.client.get_klines(symbol=symbol, interval='5m', limit=30)
                self.chart_data_cache = [float(k[4]) for k in kl]
            except: pass

            try:
                ticker = self.client.get_symbol_ticker(symbol=symbol)
                self.preco_atual_ativo = float(ticker['price'])
                
                saldo_moeda = self._get_balance(self.moeda_atual_operacao)
                if (saldo_moeda * self.preco_atual_ativo) < 5.0:
                    self.logger.info(f"✅ Saldo esgotado em {self.moeda_atual_operacao}. Operação finalizada.")
                    self.em_operacao = False
                    self.moeda_atual_operacao = None
                    self.sl_monitor_drop, self.preco_compra_ativo, self.preco_atual_ativo, self.preco_alvo_ativo, self.qtd_altcoin_ativa, self.peak_profit_perc = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                    self.chart_data_cache = []
                    self._save_state()
                    return

                if self.preco_compra_ativo <= 0:
                    self.preco_compra_ativo = self.preco_atual_ativo
                    self._save_state()

                drop_pct = ((self.preco_atual_ativo - self.preco_compra_ativo) / self.preco_compra_ativo) * 100
                self.sl_monitor_drop = drop_pct
                
                if drop_pct > self.peak_profit_perc:
                    self.peak_profit_perc = drop_pct
                    self._save_state()

                if self.peak_profit_perc >= self.trailing_activation_perc:
                    gatilho_perc = self.peak_profit_perc - self.trailing_drop_perc
                    self.preco_alvo_ativo = self.preco_compra_ativo * (1 + (gatilho_perc / 100))
                else:
                    self.preco_alvo_ativo = self.preco_compra_ativo * (1 + (self.trailing_activation_perc / 100))

                segundos_ativos = time.time() - self.operation_start_time
                horas = int(segundos_ativos // 3600)
                minutos = int((segundos_ativos % 3600) // 60)
                
                segundos_desde_switch = time.time() - self.last_switch_time
                cooldown_restante = self.golden_rule_cooldown - segundos_desde_switch
                status_cd = f" (Regra de Ouro em: {int(cooldown_restante//3600)}h {int((cooldown_restante%3600)//60)}m)" if cooldown_restante > 0 else " (Regra de Ouro: Pronta)"
                self.tempo_operacao_str = f"{horas}h {minutos}m{status_cd}"

                vender_agora = False
                motivo_venda = ""

                if drop_pct <= -self.stop_loss_perc:
                    vender_agora = True
                    motivo_venda = "STOP_LOSS"
                    self.logger.warning(f"🚨 STOP LOSS ACIONADO para {self.moeda_atual_operacao}! Queda de {drop_pct:.2f}%")
                
                elif self.peak_profit_perc >= self.trailing_activation_perc and (self.peak_profit_perc - drop_pct) >= self.trailing_drop_perc:
                    vender_agora = True
                    motivo_venda = "TRAILING_STOP"
                    self.logger.info(f"✅ TAKE PROFIT TRAILING ACIONADO para {self.moeda_atual_operacao}! Pico atingido: {self.peak_profit_perc:.2f}% | Fechando em: {drop_pct:.2f}%")

                if vender_agora:
                    _, step_size = self.get_precision_filters(symbol)
                    self.client.create_order(symbol=symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=self.format_decimal(saldo_moeda, step_size))
                    
                    if motivo_venda == "STOP_LOSS": self.trades_lost += 1
                    else: self.trades_won += 1
                    
                    self.em_operacao = False
                    self.moeda_atual_operacao = None
                    self.sl_monitor_drop, self.preco_compra_ativo, self.preco_atual_ativo, self.preco_alvo_ativo, self.qtd_altcoin_ativa, self.peak_profit_perc = 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                    self.chart_data_cache = []
                    self._save_state()
                else:
                    if segundos_ativos > self.max_hold_time_secs and (-1.0 <= drop_pct <= -0.15) and cooldown_restante <= 0:
                        self.logger.info("⏳ Bot preso em prejuízo leve por > 1h. Caçando nova oportunidade...")
                        nova_moeda = None
                        nova_cotacao = 0.0
                        for check_coin in self.manager.config.SUPPORTED_COIN_LIST:
                            if check_coin in [self.base_coin, self.moeda_atual_operacao]: continue
                            up, p_atual, _ = self.get_ema_signal(f"{check_coin}{self.base_coin}")
                            if up:
                                nova_moeda = check_coin
                                nova_cotacao = p_atual
                                break
                        
                        if nova_moeda:
                            self.logger.warning(f"👑 REGRA DE OURO! Migrando para {nova_moeda}!")
                            _, step_size = self.get_precision_filters(symbol)
                            self.client.create_order(symbol=symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=self.format_decimal(saldo_moeda, step_size))
                            time.sleep(2)
                            self.trades_lost += 1 
                            self.last_switch_time = time.time()
                            self.em_operacao = False 
                            self._save_state()
                            
                            if self.execute_real_trade(nova_moeda, nova_cotacao):
                                self.em_operacao = True
                                self.moeda_atual_operacao = nova_moeda
                            return

                    self._write_json_ui() 
            except Exception as e:
                self.logger.error(f"Erro no monitoramento: {e}")

        # ---------------- VARREDURA GRÁFICA & ANÁLISE ----------------
        for coin in self.manager.config.SUPPORTED_COIN_LIST:
            if coin == self.base_coin: continue
            symbol = f"{coin}{self.base_coin}"
            uptrend, preco_atual, var_4h = self.get_ema_signal(symbol)
            txt_preco = f"${preco_atual:.4f}"
            txt_var = f"4H: {var_4h:+.2f}%"
            
            qtd_moeda = saldos.get(coin, 0.0)
            item_linha = f"💼 {coin}: {txt_preco} ({txt_var})" if qtd_moeda > 0.000001 else f"{coin}: {txt_preco} ({txt_var})"
            
            if uptrend:
                aptas_temp.append(item_linha)
                if not self.em_operacao:
                    self.logger.info(f"🟢 {coin} | Análise: Detectada ascensão (EMA 9 > 21)! Preparando bote...")
                    sucesso = self.execute_real_trade(coin, preco_atual)
                    if sucesso:
                        self.em_operacao = True
                        self.moeda_atual_operacao = coin
            else:
                geladeira_temp.append(item_linha)
                # Só imprime a análise verbosa se não estivermos em operação
                if not self.em_operacao:
                    if var_4h < -2.0:
                        self.logger.info(f"❄️ {coin} | Análise: Em geladeira. Ativo sangrando muito ({var_4h:.2f}% nas últimas 4h).")
                    else:
                        self.logger.info(f"⏸️ {coin} | Análise: Não investido porque está abaixo da curva na regra (EMA 9 < 21).")

        self.aptas_cache = aptas_temp
        self.geladeira_cache = geladeira_temp

    def _write_json_ui(self):
        try:
            btc_ticker = self.client.get_ticker(symbol=f"BTC{self.base_coin}")
            btc_price = float(btc_ticker['lastPrice'])
            btc_change = float(btc_ticker['priceChangePercent'])
        except Exception:
            btc_price, btc_change = 0.0, 0.0
            
        if self.peak_profit_perc >= self.trailing_activation_perc:
            txt_alvo = f"🚀 TRAILING ATIVO! Pico: {self.peak_profit_perc:.2f}% | Trava de Venda Armada em: {self.peak_profit_perc - self.trailing_drop_perc:.2f}%"
        else:
            txt_alvo = f"[🎯] Gatilho Trailing: {self.trailing_activation_perc:.2f}% | [🛑] SL: -{self.stop_loss_perc:.2f}% (Var Atual: {self.sl_monitor_drop:+.2f}%)"
            
        status_data = {
            "coin": self.moeda_atual_operacao if self.em_operacao else self.base_coin,
            "status": "Em Operação (Alvo/Stop)" if self.em_operacao else "Mapeando Tendências",
            "btc_price": btc_price,
            "btc_change": btc_change,
            "buy_price": self.preco_compra_ativo,
            "current_price": self.preco_atual_ativo,
            "target_price": self.preco_alvo_ativo,
            "active_qty": self.qtd_altcoin_ativa,          
            "buy_time": self.operation_start_time,         
            "chart_data": self.chart_data_cache,
            "trades_won": self.trades_won,     
            "trades_lost": self.trades_lost,   
            "detalhe_atual": f"[⏳] Duração: {self.tempo_operacao_str} | {txt_alvo}",
            "aptas": self.aptas_cache,
            "geladeira": self.geladeira_cache
        }

        try:
            with open("bot_status.json", "w", encoding="utf-8") as f: 
                json.dump(status_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass