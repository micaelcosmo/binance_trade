import time
import json
import math
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
        
        # --- MATEMÁTICA DA OPERAÇÃO ---
        self.taxa_maker = 0.10
        self.margem_poeira = 0.80
        self.lucro_liquido = 0.60
        self.target_perc = self.taxa_maker * 2 + self.margem_poeira + self.lucro_liquido 
        
        # 🛑 AIRBAG DE SEGURANÇA
        self.stop_loss_perc = 2.0 
        self.sl_monitor_drop = 0.0 
        
        # --- ESTADOS PARA A UI ---
        self.preco_compra_ativo = 0.0
        self.preco_atual_ativo = 0.0
        self.preco_alvo_ativo = 0.0
        self.chart_data_cache = [] # Guarda as velas do minigráfico
        
        self.em_operacao = False
        self.moeda_atual_operacao = None
        self.aptas_cache = []
        self.geladeira_cache = []

    def initialize(self):
        self.logger.info("🚀 Inicializando Profit Gain Pro (MODO PRODUÇÃO)...")
        self._write_json_ui()

    def scout(self):
        self.logger.info(f"[HEARTBEAT] 💓 Motor executando varredura. Base oficial: {self.base_coin}")
        self.scan_market()
        self._write_json_ui()

    def update_values(self):
        self._write_json_ui()

    # ==========================================
    # UTILITÁRIOS DA BINANCE
    # ==========================================
    
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
            
            var_4h = 0.0
            if preco_4h_atras > 0:
                var_4h = ((preco_atual - preco_4h_atras) / preco_4h_atras) * 100
                
            ultima_linha = df.iloc[-1]
            uptrend = ultima_linha['EMA_9'] > ultima_linha['EMA_21']
            
            return uptrend, preco_atual, var_4h
        except Exception:
            return False, 0.0, 0.0

    # ==========================================
    # NÚCLEO DE EXECUÇÃO
    # ==========================================

    def execute_real_trade(self, coin, preco_atual):
        symbol = f"{coin}{self.base_coin}"
        saldo_base = self._get_balance(self.base_coin)
        
        if saldo_base < 6.0: return False

        comprou_mercado = False
        try:
            self.logger.info(f"🚀 ENTRADA REAL: Comprando {symbol} a mercado...")
            tick_size, step_size = self.get_precision_filters(symbol)
            
            compra_usdt = saldo_base * 0.99 
            quote_qty_str = self.format_decimal(compra_usdt, 0.01) 
            
            self.client.create_order(symbol=symbol, side=SIDE_BUY, type=ORDER_TYPE_MARKET, quoteOrderQty=quote_qty_str)
            comprou_mercado = True
            time.sleep(2) 
            
            saldo_moeda = self._get_balance(coin)
            qtd_vender_str = self.format_decimal(saldo_moeda, step_size)
            
            if float(qtd_vender_str) == 0: 
                self.logger.warning("Aviso: Saldo zerado logo após a compra. A Binance pode estar com lag.")
                return True

            preco_venda = float(preco_atual) * (1 + (self.target_perc / 100))
            preco_venda_str = self.format_decimal(preco_venda, tick_size)
            
            self.logger.info(f"🎯 Pendurando alvo de lucro (Sell LIMIT) em {preco_venda_str}...")
            self.client.create_order(symbol=symbol, side=SIDE_SELL, type=ORDER_TYPE_LIMIT, timeInForce=TIME_IN_FORCE_GTC, quantity=qtd_vender_str, price=preco_venda_str)
            
            self.preco_compra_ativo = float(preco_atual)
            self.preco_alvo_ativo = float(preco_venda_str)
            self.preco_atual_ativo = float(preco_atual)
            
            return True

        except Exception as e:
            self.logger.error(f"❌ ERRO CRÍTICO na corretora: {e}")
            if comprou_mercado:
                self.logger.warning(f"⚠️ Operação PARCIAL. O bot comprou {coin}, mas falhou no LIMIT. O monitor assumirá.")
                return True
            return False

    def scan_market(self):
        self.logger.info("📊 Mapeando gráficos, carteira e Stop Loss...")
        aptas_temp = []
        geladeira_temp = []
        
        try:
            acc = self.client.get_account()
            saldos = {b['asset']: float(b['free']) + float(b['locked']) for b in acc['balances']}
        except Exception:
            saldos = {}

        # ---------------- RECUPERAÇÃO DE ESTADO ----------------
        if not self.em_operacao:
            self.preco_compra_ativo, self.preco_atual_ativo, self.preco_alvo_ativo = 0.0, 0.0, 0.0
            self.chart_data_cache = []
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
                                self.logger.info(f"🔄 Recuperação de Estado: Detectado ~${valor_dolar:.2f} em {c}.")
                                self.em_operacao = True
                                self.moeda_atual_operacao = c
                                break
                        except: pass

        # ---------------- MONITORAMENTO (AIRBAG E MINIGRÁFICO) ----------------
        if self.em_operacao:
            symbol = f"{self.moeda_atual_operacao}{self.base_coin}"
            
            # Tenta pegar os preços do minigráfico (últimas 30 velas de 5m = 2h30)
            try:
                kl = self.client.get_klines(symbol=symbol, interval='5m', limit=30)
                self.chart_data_cache = [float(k[4]) for k in kl]
            except: pass

            try:
                open_orders = self.client.get_open_orders(symbol=symbol)
                if open_orders:
                    sell_order = open_orders[0]
                    self.preco_alvo_ativo = float(sell_order['price'])
                    self.preco_compra_ativo = self.preco_alvo_ativo / (1 + (self.target_perc / 100))
                    
                    ticker = self.client.get_symbol_ticker(symbol=symbol)
                    self.preco_atual_ativo = float(ticker['price'])
                    
                    drop_pct = ((self.preco_atual_ativo - self.preco_compra_ativo) / self.preco_compra_ativo) * 100
                    self.sl_monitor_drop = drop_pct
                    
                    if drop_pct <= -self.stop_loss_perc:
                        self.logger.warning(f"🚨 STOP LOSS ACIONADO para {self.moeda_atual_operacao}! Queda de {drop_pct:.2f}%")
                        self.client.cancel_order(symbol=symbol, orderId=sell_order['orderId'])
                        time.sleep(1) 
                        saldo_moeda = self._get_balance(self.moeda_atual_operacao)
                        _, step_size = self.get_precision_filters(symbol)
                        qtd_vender_str = self.format_decimal(saldo_moeda, step_size)
                        self.client.create_order(symbol=symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=qtd_vender_str)
                        self.em_operacao = False
                        self.moeda_atual_operacao = None
                        self.sl_monitor_drop, self.preco_compra_ativo, self.preco_atual_ativo, self.preco_alvo_ativo = 0.0, 0.0, 0.0, 0.0
                        self.chart_data_cache = []
                    else:
                        self.logger.info(f"[STATUS] ⏳ Aguardando Alvo (+{self.target_perc:.2f}%) ou Stop (-{self.stop_loss_perc:.2f}%) para {self.moeda_atual_operacao}... Posição: {drop_pct:.2f}%")
                else:
                    qtd = saldos.get(self.moeda_atual_operacao, 0.0)
                    saldo_dolar = qtd * float(self.client.get_symbol_ticker(symbol=symbol)['price']) if qtd > 0 else 0.0
                    if saldo_dolar < 5.0:
                        self.logger.info(f"✅ TAKE PROFIT CONFIRMADO para {self.moeda_atual_operacao}! Dinheiro no bolso.")
                    else:
                        self.logger.warning(f"⚠️ Ordem limite ausente. Forçando venda a mercado para proteção.")
                        _, step_size = self.get_precision_filters(symbol)
                        self.client.create_order(symbol=symbol, side=SIDE_SELL, type=ORDER_TYPE_MARKET, quantity=self.format_decimal(qtd, step_size))
                    
                    self.em_operacao = False
                    self.moeda_atual_operacao = None
                    self.sl_monitor_drop, self.preco_compra_ativo, self.preco_atual_ativo, self.preco_alvo_ativo = 0.0, 0.0, 0.0, 0.0
                    self.chart_data_cache = []
            except Exception as e:
                self.logger.error(f"Erro no monitoramento: {e}")

        # ---------------- VARREDURA GRÁFICA DAS LISTAS ----------------
        for coin in self.manager.config.SUPPORTED_COIN_LIST:
            if coin == self.base_coin: continue
            symbol = f"{coin}{self.base_coin}"
            
            uptrend, preco_atual, var_4h = self.get_ema_signal(symbol)
            
            txt_preco = f"${preco_atual:.4f}"
            txt_var = f"4H: {var_4h:+.2f}%"
            
            qtd_moeda = saldos.get(coin, 0.0)
            if qtd_moeda > 0.000001:
                item_linha = f"💼 {coin}: {txt_preco} ({txt_var})"
            else:
                item_linha = f"{coin}: {txt_preco} ({txt_var})"
            
            if uptrend:
                aptas_temp.append(item_linha)
                if not self.em_operacao:
                    sucesso = self.execute_real_trade(coin, preco_atual)
                    if sucesso:
                        self.em_operacao = True
                        self.moeda_atual_operacao = coin
            else:
                geladeira_temp.append(item_linha)

        self.aptas_cache = aptas_temp
        self.geladeira_cache = geladeira_temp

    def _write_json_ui(self):
        try:
            btc_ticker = self.client.get_ticker(symbol=f"BTC{self.base_coin}")
            btc_price = float(btc_ticker['lastPrice'])
            btc_change = float(btc_ticker['priceChangePercent'])
        except Exception:
            btc_price, btc_change = 0.0, 0.0
            
        status_data = {
            "coin": self.moeda_atual_operacao if self.em_operacao else self.base_coin,
            "status": "Em Operação (Alvo/Stop)" if self.em_operacao else "Mapeando Tendências",
            "btc_price": btc_price,
            "btc_change": btc_change,
            "buy_price": self.preco_compra_ativo,
            "current_price": self.preco_atual_ativo,
            "target_price": self.preco_alvo_ativo,
            "chart_data": self.chart_data_cache, # <--- Enviando os dados do minigráfico!
            "detalhe_atual": f"[🎯] Alvo Global: {self.target_perc:.2f}% | [🛑] SL: -{self.stop_loss_perc:.2f}% (Variação Atual: {self.sl_monitor_drop:+.2f}%)",
            "aptas": self.aptas_cache, # Listas salvas no cache real
            "geladeira": self.geladeira_cache
        }

        try:
            with open("bot_status.json", "w", encoding="utf-8") as f: 
                json.dump(status_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass