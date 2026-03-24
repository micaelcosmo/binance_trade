import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import sys
import time
import json
import os

from binance_trade_bot.config import Config
from binance.client import Client

class BinanceBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Binance Trade Bot Pro - Dashboard")
        self.root.geometry("1300x850") 
        
        try:
            self.bot_config = Config()
            self.current_strategy = getattr(self.bot_config, 'STRATEGY', 'default').lower()
        except Exception:
            self.current_strategy = 'default'
            
        self.gui_state_file = "gui_state.json"
        self.saldo_inicial = 0.0
        self.saldo_atual = 0.0
        self._load_gui_state()
        
        self.bg_main = "#121212"
        self.bg_frame = "#1e1e1e"
        self.fg_text = "#e8eaed"
        self.accent_blue = "#8ab4f8"
        self.accent_green = "#81c995"
        self.accent_red = "#f28b82"
        self.accent_yellow = "#fde293"
        self.btc_gold = "#f2a900"
        
        self.root.configure(bg=self.bg_main)
        
        self.top_frame = tk.Frame(root, bg=self.bg_frame, pady=12)
        self.top_frame.pack(fill=tk.X, side=tk.TOP)
        
        tk.Label(self.top_frame, text=f"Modo: {self.current_strategy.upper()}", bg=self.bg_frame, fg=self.accent_yellow, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=15)
        
        tk.Button(self.top_frame, text="RUN > Iniciar Bot", command=self.start_bot, bg=self.accent_blue, font=("Segoe UI", 10, "bold"), width=15).pack(side=tk.LEFT, padx=15)
        tk.Button(self.top_frame, text="STOP > Parar Bot", command=self.stop_bot, bg=self.accent_red, font=("Segoe UI", 10, "bold"), width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(self.top_frame, text="CLR > Limpar Log", command=self.clear_log, bg="#3c4043", fg="white", font=("Segoe UI", 10, "bold"), width=15).pack(side=tk.RIGHT, padx=15)
        tk.Button(self.top_frame, text="♻ Atualizar Inicial", command=self.reset_initial_balance, bg="#5f6368", fg="white", font=("Segoe UI", 10, "bold"), width=18).pack(side=tk.RIGHT, padx=5)
        
        self.metrics_frame = tk.Frame(root, bg=self.bg_frame, pady=15)
        self.metrics_frame.pack(fill=tk.X, side=tk.TOP, padx=15, pady=15)

        txt_ini = f"${self.saldo_inicial:.2f}" if self.saldo_inicial > 0 else "--"
        self.lbl_inicial = tk.Label(self.metrics_frame, text=f"[S] Inicial: {txt_ini}", bg=self.bg_frame, fg=self.accent_blue, font=("Segoe UI", 11, "bold"), width=25, anchor="w")
        self.lbl_inicial.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.lbl_atual = tk.Label(self.metrics_frame, text="[$] Atual: --", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 11, "bold"), width=25, anchor="w")
        self.lbl_atual.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.lbl_pl = tk.Label(self.metrics_frame, text="[%] P/L Total: --", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 11, "bold"), width=30, anchor="w")
        self.lbl_pl.grid(row=0, column=2, padx=10, pady=5, sticky="w")

        # --- LARGURAS AUMENTADAS AQUI (Largura de Status passou de 25 para 35) ---
        self.lbl_status = tk.Label(self.metrics_frame, text="STATUS: Parado", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 10, "bold"), width=35, anchor="w")
        self.lbl_status.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.lbl_trades = tk.Label(self.metrics_frame, text="TRADES: 0 | W: 0 | L: 0 (0.0%)", bg=self.bg_frame, fg=self.accent_yellow, font=("Segoe UI", 10, "bold"), width=35, anchor="w")
        self.lbl_trades.grid(row=1, column=1, padx=10, pady=5, sticky="w")
        self.lbl_ping = tk.Label(self.metrics_frame, text="PING: -- ms", bg=self.bg_frame, fg="#bdc1c6", font=("Segoe UI", 10), width=30, anchor="w")
        self.lbl_ping.grid(row=1, column=2, padx=10, pady=5, sticky="w")

        self.lbl_cur_coin = tk.Label(self.metrics_frame, text="Current Coin: BUSCANDO...", bg=self.bg_frame, fg=self.accent_blue, font=("Segoe UI", 10, "bold"), width=25, anchor="w")
        self.lbl_cur_coin.grid(row=2, column=0, padx=10, pady=(15, 5), sticky="w")
        
        if self.current_strategy == 'profit_gain':
            self.lbl_buy_price = tk.Label(self.metrics_frame, text="[🛒] Compra Est.: --", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 10, "bold"), width=65, anchor="w")
            self.lbl_buy_price.grid(row=2, column=1, columnspan=2, padx=10, pady=(15, 5), sticky="w")
            
            self.lbl_cur_price = tk.Label(self.metrics_frame, text="[💲] Atual: --", bg=self.bg_frame, fg=self.accent_blue, font=("Segoe UI", 10, "bold"), width=65, anchor="w")
            self.lbl_cur_price.grid(row=3, column=1, columnspan=2, padx=10, pady=5, sticky="w")
            
            self.lbl_tgt_price = tk.Label(self.metrics_frame, text="[🎯] Alvo (Venda): --", bg=self.bg_frame, fg=self.accent_green, font=("Segoe UI", 10, "bold"), width=65, anchor="w")
            self.lbl_tgt_price.grid(row=4, column=1, columnspan=2, padx=10, pady=5, sticky="w")
            
            self.lbl_btc = tk.Label(self.metrics_frame, text="BTC: Buscando...", bg=self.bg_frame, fg=self.btc_gold, font=("Segoe UI", 10, "bold"), width=40, anchor="w")
            self.lbl_btc.grid(row=2, column=3, padx=10, pady=(15, 5), sticky="w")

            # --- LARGURA AUMENTADA AQUI (Largura de Detalhes passou de 90 para 110) ---
            self.lbl_det_atu = tk.Label(self.metrics_frame, text="Análise: Aguardando...", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 10), width=110, anchor="w")
            self.lbl_det_atu.grid(row=5, column=1, columnspan=3, padx=10, pady=5, sticky="w")
            
            # ====== O MINIGRÁFICO AUMENTADO (De 220x80 para 280x110) ======
            self.canvas_chart = tk.Canvas(self.metrics_frame, bg="#000000", width=280, height=110, highlightthickness=1, highlightbackground="#3c4043")
            self.canvas_chart.grid(row=1, column=4, rowspan=3, padx=(0,10), pady=5, sticky="e")
            self.lbl_chart_title = tk.Label(self.metrics_frame, text="Mini-Gráfico (Inativo)", bg=self.bg_frame, fg="#9aa0a6", font=("Segoe UI", 8, "bold"))
            self.lbl_chart_title.grid(row=4, column=4, sticky="e", padx=(0,10))
            
        else:
            self.lbl_last_jump = tk.Label(self.metrics_frame, text="Último Salto: Nenhum", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 10), width=45, anchor="w")
            self.lbl_last_jump.grid(row=2, column=1, padx=10, pady=(15, 5), sticky="w")
            
            self.lbl_btc = tk.Label(self.metrics_frame, text="BTC: Buscando...", bg=self.bg_frame, fg=self.btc_gold, font=("Segoe UI", 10, "bold"), width=30, anchor="w")
            self.lbl_btc.grid(row=2, column=2, padx=10, pady=(15, 5), sticky="w")
            
            self.lbl_rota = tk.Label(self.metrics_frame, text="Rota: Analisando...", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 10, "bold"), width=35, anchor="nw")
            self.lbl_rota.grid(row=3, column=0, rowspan=3, padx=10, pady=(5,0), sticky="nw") 

            self.lbl_qtd_prev = tk.Label(self.metrics_frame, text="[⏪] Anterior (--): -- | Venda: -- | Poeira: --", bg=self.bg_frame, fg="#9aa0a6", font=("Segoe UI", 10, "bold"), width=70, anchor="w")
            self.lbl_qtd_prev.grid(row=3, column=1, columnspan=2, padx=10, pady=(5, 2), sticky="w")
            
            self.lbl_qtd = tk.Label(self.metrics_frame, text="[📦] Atual (--): -- | Venda: -- | Poeira: --", bg=self.bg_frame, fg=self.accent_green, font=("Segoe UI", 10, "bold"), width=70, anchor="w")
            self.lbl_qtd.grid(row=4, column=1, columnspan=2, padx=10, pady=(0, 2), sticky="w")
            
            self.lbl_trailing = tk.Label(self.metrics_frame, text="🎯 Trailing Global: Aguardando Inicialização...", bg=self.bg_frame, fg=self.accent_yellow, font=("Segoe UI", 10, "bold"), width=70, anchor="w")
            self.lbl_trailing.grid(row=5, column=1, columnspan=2, padx=10, pady=(0, 5), sticky="w")

        self.content_frame = tk.Frame(root, bg=self.bg_main)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        self.log_area = scrolledtext.ScrolledText(self.content_frame, wrap=tk.WORD, bg="#000000", fg=self.accent_green, font=("Consolas", 10))
        self.log_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.right_panel = tk.Frame(self.content_frame, bg=self.bg_frame, width=300)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        self.right_panel.pack_propagate(False)

        title_hot = "🔥 APTAS (>= 2%)" if self.current_strategy == 'default' else "🟢 SINAIS H4 CONFIRMADOS"
        tk.Label(self.right_panel, text=title_hot, bg=self.bg_frame, fg=self.accent_green, font=("Segoe UI", 10, "bold")).pack(pady=(10,5))
        self.list_hot = tk.Listbox(self.right_panel, bg="#000000", fg=self.accent_green, font=("Consolas", 9), selectbackground=self.bg_frame, highlightthickness=0)
        self.list_hot.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

        title_cold = "❄️ GELADEIRA (< 2%)" if self.current_strategy == 'default' else "❄️ GELADEIRA (QUEDA)"
        tk.Label(self.right_panel, text=title_cold, bg=self.bg_frame, fg=self.accent_red, font=("Segoe UI", 10, "bold")).pack(pady=(5,5))
        self.list_cold = tk.Listbox(self.right_panel, bg="#000000", fg=self.accent_red, font=("Consolas", 9), selectbackground=self.bg_frame, highlightthickness=0)
        self.list_cold.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

        self.process = None
        self.bot_running = False

    def _load_gui_state(self):
        if os.path.exists(self.gui_state_file):
            try:
                with open(self.gui_state_file, "r") as f:
                    data = json.load(f)
                    self.saldo_inicial = data.get("saldo_inicial", 0.0)
            except: pass

    def _save_gui_state(self):
        try:
            with open(self.gui_state_file, "w") as f:
                json.dump({"saldo_inicial": self.saldo_inicial}, f)
        except: pass

    def reset_initial_balance(self):
        if self.saldo_atual > 0:
            self.saldo_inicial = self.saldo_atual
            self._save_gui_state()
            self.lbl_inicial.config(text=f"[S] Inicial: ${self.saldo_inicial:.2f}")
            self.log_message("\n[✓] ♻️ Saldo Inicial sincronizado com sucesso!\n")

    def draw_mini_chart(self, data, coin, buy_price=0.0, buy_time=0.0):
        self.canvas_chart.delete("all")
        if not data or len(data) < 2:
            self.lbl_chart_title.config(text=f"{coin} - Aguardando Dados...")
            return

        self.lbl_chart_title.config(text=f"{coin} - Últimas 2h30 (5m)", fg=self.accent_blue)
        
        w = int(self.canvas_chart['width'])
        h = int(self.canvas_chart['height'])
        pad = 5
        
        min_val = min(data)
        max_val = max(data)
        val_range = max_val - min_val if max_val != min_val else 1
        
        color = self.accent_green if data[-1] >= data[0] else self.accent_red
        
        points = []
        x_step = (w - 2*pad) / (len(data) - 1)
        for i, val in enumerate(data):
            x = pad + i * x_step
            y = pad + (h - 2*pad) * (1 - (val - min_val) / val_range)
            points.append(x)
            points.append(y)
            
        self.canvas_chart.create_line(points, fill=color, width=2, smooth=True)

        if buy_price > 0 and (min_val <= buy_price <= max_val):
            y_buy = pad + (h - 2*pad) * (1 - (buy_price - min_val) / val_range)
            self.canvas_chart.create_line(pad, y_buy, w-pad, y_buy, fill="#f2a900", dash=(2, 2))
            if buy_time > 0:
                diff_sec = time.time() - buy_time
                candles_ago = diff_sec / 300.0 
                idx_compra = (len(data) - 1) - candles_ago
                if 0 <= idx_compra <= len(data) - 1:
                    x_buy = pad + idx_compra * x_step
                    raio = 3
                    self.canvas_chart.create_oval(x_buy-raio, y_buy-raio, x_buy+raio, y_buy+raio, fill="#f2a900", outline="#ffffff", width=1)

    def check_bot_state_json(self):
        if self.bot_running and os.path.exists("bot_status.json"):
            try:
                with open("bot_status.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if data:
                    if self.current_strategy == 'profit_gain':
                        if "coin" in data:
                            coin = data.get('coin', 'BUSCANDO...')
                            self.lbl_cur_coin.config(text=f"Current Coin: {coin}")
                            
                            btc_p = data.get('btc_price', 0.0)
                            btc_c = data.get('btc_change', 0.0)
                            cor_btc = self.accent_green if btc_c >= 0 else self.accent_red
                            self.lbl_btc.config(text=f"BTC: ${btc_p:,.2f} | Var: {btc_c:+.2f}%", fg=cor_btc)
                            
                            bp = data.get('buy_price', 0.0)
                            cp = data.get('current_price', 0.0)
                            tp = data.get('target_price', 0.0)
                            qty = data.get('active_qty', 0.0)
                            b_time = data.get('buy_time', 0.0)
                            
                            if bp > 0 and qty > 0:
                                buy_usdt = bp * qty
                                cur_usdt = cp * qty
                                tgt_usdt = tp * qty
                                self.lbl_buy_price.config(text=f"[🛒] Compra Est.: ${bp:.6f}   |   {buy_usdt:.2f} USDT ⇌ {qty:.4f} {coin}")
                                self.lbl_cur_price.config(text=f"[💲] Atual: ${cp:.6f}   |   {cur_usdt:.2f} USDT ⇌ {qty:.4f} {coin}")
                                self.lbl_tgt_price.config(text=f"[🎯] Alvo (Venda): ${tp:.6f}   |   {tgt_usdt:.2f} USDT ⇌ {qty:.4f} {coin}")
                            else:
                                self.lbl_buy_price.config(text="[🛒] Compra Est.: --")
                                self.lbl_cur_price.config(text="[💲] Atual: --")
                                self.lbl_tgt_price.config(text="[🎯] Alvo (Venda): --")
                                
                            self.lbl_det_atu.config(text=f"{data.get('detalhe_atual', '--')}")
                            
                            tw = data.get("trades_won", 0)
                            tl = data.get("trades_lost", 0)
                            total_t = tw + tl
                            win_rate = (tw / total_t * 100) if total_t > 0 else 0.0
                            self.lbl_trades.config(text=f"TRADES: {total_t} | W: {tw} | L: {tl} ({win_rate:.1f}%)")
                            
                            if "status" in data:
                                cor = self.accent_yellow if "Em Operação" in data['status'] else self.accent_blue
                                if "Crash" in data['status']: cor = self.accent_red
                                self.lbl_status.config(text=f"STATUS: {data['status']}", fg=cor)
                            
                            chart_data = data.get('chart_data', [])
                            if chart_data:
                                self.draw_mini_chart(chart_data, coin, bp, b_time)
                            else:
                                self.canvas_chart.delete("all")
                                self.lbl_chart_title.config(text="Mini-Gráfico (Inativo)", fg="#9aa0a6")

                            hot = data.get('aptas', [])
                            cold = data.get('geladeira', [])
                            self.list_hot.delete(0, tk.END)
                            for c in hot: self.list_hot.insert(tk.END, c)
                            self.list_cold.delete(0, tk.END)
                            for c in cold: self.list_cold.insert(tk.END, c)
                            
                    else:
                        if "coin" in data:
                            self.lbl_cur_coin.config(text=f"Current Coin: {data.get('coin', 'BUSCANDO...')}")
                            self.lbl_last_jump.config(text=f"Último Salto: {data.get('last_jump', 'Nenhum')}")
                            
                            btc_p = data.get('btc_price', 0.0)
                            btc_c = data.get('btc_change', 0.0)
                            cor_btc = self.accent_green if btc_c >= 0 else self.accent_red
                            self.lbl_btc.config(text=f"BTC: ${btc_p:,.2f} | Var: {btc_c:+.2f}%", fg=cor_btc)
                            
                            self.lbl_rota.config(text=f"Rota: {data.get('route', 'Analisando...')}")
                            
                            if "status" in data:
                                cor = self.accent_yellow if "Segurando" in data['status'] else self.accent_blue
                                if "Crash" in data['status']: cor = self.accent_red
                                self.lbl_status.config(text=f"STATUS: {data['status']}", fg=cor)

                            p_coin = data.get('prev_coin', 'Nenhuma')
                            pq = data.get('prev_qty', 0.0)
                            ps = data.get('prev_sell', 0.0)
                            pd = data.get('prev_dust', 0.0)
                            
                            if p_coin in ["Nenhuma", "USDT"]:
                                self.lbl_qtd_prev.config(text=f"[⏪] Anterior ({p_coin}): -- | Venda Real: -- | Poeira: --", fg="#9aa0a6")
                            else:
                                self.lbl_qtd_prev.config(text=f"[⏪] Anterior ({p_coin}): {pq:.4f} | Venda Real: {ps:.4f} | Poeira: {pd:.4f}", fg="#9aa0a6")
                            
                            c_coin = data.get('coin', 'BUSCANDO...')
                            cq = data.get('current_qty', 0.0)
                            sq = data.get('sell_qty', 0.0)
                            du = data.get('dust', 0.0)

                            if cq == 0.0:
                                self.lbl_qtd.config(text=f"[📦] Atual ({c_coin}): -- | Venda Real: -- | Poeira: --", fg=self.fg_text)
                            else:
                                self.lbl_qtd.config(text=f"[📦] Atual ({c_coin}): {cq:.4f} | Venda Real: {sq:.4f} | Poeira: {du:.4f}", fg=self.accent_green)

                            init_bal = data.get("init_bal", 0.0)
                            peak = data.get("peak_profit", 0.0)
                            curr_p = data.get("curr_profit", 0.0)
                            tp = data.get("global_tp", 3.5)
                            drop = data.get("trailing_drop", 0.4)

                            if init_bal > 0:
                                if peak > 0:
                                    self.lbl_trailing.config(text=f"🎯 Trailing [ATIVO]: Gatilho {tp}% | Pico: {peak:.2f}% | Atual: {curr_p:.2f}% (Vende se recuar {drop}%)", fg=self.accent_green)
                                else:
                                    self.lbl_trailing.config(text=f"🎯 Meta Global: Gatilho em {tp}% | Lucro Atual: {curr_p:.2f}%", fg=self.accent_yellow)
                            else:
                                self.lbl_trailing.config(text="🎯 Meta Global: Calculando saldo base...", fg=self.fg_text)

                            hot = data.get('hot_coins', [])
                            cold = data.get('cold_coins', [])
                            self.list_hot.delete(0, tk.END)
                            for c in hot: self.list_hot.insert(tk.END, c)
                            self.list_cold.delete(0, tk.END)
                            for c in cold: self.list_cold.insert(tk.END, c)

            except Exception: pass 
                
        self.root.after(2000, self.check_bot_state_json)

    def read_output(self):
        if self.process:
            for line in iter(self.process.stdout.readline, ''):
                if self.current_strategy == 'profit_gain':
                    if "Mapeando EMA" in line:
                        self.root.after(0, lambda: self.lbl_status.config(text="STATUS: Escaneando o Mercado...", fg=self.accent_blue))
                    elif "LIMIT em" in line:
                        self.root.after(0, lambda: self.lbl_status.config(text="STATUS: Operação Executada!", fg=self.accent_green))
                    if "TAKE PROFIT!" in line:
                        self.root.after(0, lambda: self.lbl_status.config(text="STATUS: Vendendo (Lucro)!", fg=self.accent_green))
                    if "STOP LOSS" in line or "TIMEOUT!" in line:
                        self.root.after(0, lambda: self.lbl_status.config(text="STATUS: Vendendo (Loss/Timeout)!", fg=self.accent_red))
                else:
                    if "jumping from" in line or "Jumping from" in line:
                        self.root.after(0, lambda: self.lbl_status.config(text="STATUS: Realizando Salto (Jump)...", fg=self.accent_green))

                self.log_message(line)
            
            self.process.stdout.close()
            self.process.wait()
            
            if self.bot_running:
                self.root.after(0, lambda: self.lbl_status.config(text="STATUS: Erro/Crash (Veja o Log)", fg=self.accent_red))
                self.bot_running = False

    def get_total_usdt_balance(self, client, bridge_symbol):
        try:
            acc = client.get_account()
            tickers = {t['symbol']: float(t['price']) for t in client.get_symbol_ticker()}
            total_usdt = 0.0
            for b in acc['balances']:
                free = float(b['free']) + float(b['locked'])
                if free > 0:
                    asset = b['asset']
                    if asset == bridge_symbol: total_usdt += free
                    else:
                        sym = f"{asset}{bridge_symbol}"
                        if sym in tickers: total_usdt += free * tickers[sym]
            return total_usdt
        except: return 0.0

    def update_stats_loop(self):
        try:
            config = Config()
            client = Client(config.BINANCE_API_KEY, config.BINANCE_API_SECRET_KEY, tld=config.BINANCE_TLD)
            bridge = config.BRIDGE.symbol if hasattr(config.BRIDGE, 'symbol') else getattr(config, 'BRIDGE', 'USDT')
            
            for _ in range(3):
                start_t = time.time()
                total_atual = self.get_total_usdt_balance(client, bridge)
                ping = int((time.time() - start_t) * 1000)
                if total_atual > 0:
                    self.saldo_atual = total_atual
                    if self.saldo_inicial == 0.0:
                        self.saldo_inicial = total_atual
                        self._save_gui_state()
                        
                    self.root.after(0, lambda u=self.saldo_inicial, p=ping: [
                        self.lbl_inicial.config(text=f"[S] Inicial: ${u:.2f}"),
                        self.lbl_ping.config(text=f"PING: {p} ms")
                    ])
                    break
                time.sleep(1)
            
            while self.bot_running:
                start_t = time.time()
                total_atual = self.get_total_usdt_balance(client, bridge)
                ping = int((time.time() - start_t) * 1000)
                
                if total_atual > 0:
                    self.saldo_atual = total_atual
                    
                if self.saldo_inicial > 0 and total_atual > 0:
                    pl = total_atual - self.saldo_inicial
                    pl_perc = (pl / self.saldo_inicial) * 100
                    cor_pl = self.accent_green if pl >= 0 else self.accent_red
                else:
                    pl = pl_perc = 0
                    cor_pl = self.fg_text

                if total_atual > 0:
                    self.root.after(0, lambda a=total_atual, p=pl, pp=pl_perc, c=cor_pl, pi=ping: [
                        self.lbl_atual.config(text=f"[$] Atual: ${a:.2f}"),
                        self.lbl_pl.config(text=f"[%] P/L Total: ${p:.2f} ({pp:.2f}%)", fg=c),
                        self.lbl_ping.config(text=f"PING: {pi} ms")
                    ])
                time.sleep(15)
        except: pass

    def start_bot(self):
        self.log_message("[!] Iniciando...\n")
        self.lbl_status.config(text="STATUS: Booting...", fg=self.fg_text)
        with open("bot_status.json", "w") as f: json.dump({}, f)
        
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        self.bot_running = True
        self.process = subprocess.Popen(
            [sys.executable, "-m", "binance_trade_bot"], 
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding='utf-8', errors='replace', env=env
        )
        threading.Thread(target=self.read_output, daemon=True).start()
        threading.Thread(target=self.update_stats_loop, daemon=True).start()
        self.check_bot_state_json()

    def stop_bot(self):
        if self.process: self.process.terminate()
        self.bot_running = False
        self.lbl_status.config(text="STATUS: Parado", fg=self.fg_text)

    def clear_log(self): self.log_area.delete(1.0, tk.END)

    def log_message(self, message):
        def _append_and_clean():
            self.log_area.insert(tk.END, message)
            self.log_area.yview(tk.END)
            linhas_totais = int(self.log_area.index('end-1c').split('.')[0])
            if linhas_totais > 1500: self.log_area.delete('1.0', '500.0')
        self.root.after(0, _append_and_clean)

if __name__ == "__main__":
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

    root = tk.Tk()
    app = BinanceBotGUI(root)
    root.mainloop()