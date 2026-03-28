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
        
        self.bg_main = "#0b0e11" 
        self.bg_frame = "#1e2329" 
        self.fg_text = "#eaecef" 
        self.accent_blue = "#8ab4f8"
        self.accent_green = "#0ecb81" 
        self.accent_red = "#f6465d" 
        self.accent_yellow = "#fcd535" 
        self.btc_gold = "#f2a900"
        self.neutral_obs = "#eaecef"
        self.geladeira_dark = "#5f6368"
        
        self.root.configure(bg=self.bg_main)
        
        self.top_frame = tk.Frame(root, bg=self.bg_frame, pady=12)
        self.top_frame.pack(fill=tk.X, side=tk.TOP)
        
        tk.Label(self.top_frame, text=f"Modo: {self.current_strategy.upper()}", bg=self.bg_frame, fg=self.accent_yellow, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=15)
        
        tk.Button(self.top_frame, text="RUN > Iniciar Bot", command=self.start_bot, bg=self.accent_blue, font=("Segoe UI", 10, "bold"), width=15).pack(side=tk.LEFT, padx=15)
        tk.Button(self.top_frame, text="STOP > Parar Bot", command=self.stop_bot, bg=self.accent_red, font=("Segoe UI", 10, "bold"), width=15).pack(side=tk.LEFT, padx=5)
        
        tk.Button(self.top_frame, text="CLR > Limpar Log", command=self.clear_log, bg="#3c4043", fg="white", font=("Segoe UI", 10, "bold"), width=15).pack(side=tk.RIGHT, padx=15)
        tk.Button(self.top_frame, text="♻ Atualizar Inicial", command=self.reset_initial_balance, bg="#5f6368", fg="white", font=("Segoe UI", 10, "bold"), width=18).pack(side=tk.RIGHT, padx=5)
        tk.Button(self.top_frame, text="[ 0 ] Zerar Placar", command=self.reset_scoreboard, bg="#5f6368", fg="white", font=("Segoe UI", 10, "bold"), width=16).pack(side=tk.RIGHT, padx=5)
        
        self.metrics_frame = tk.Frame(root, bg=self.bg_frame, pady=15)
        self.metrics_frame.pack(fill=tk.X, side=tk.TOP, padx=15, pady=15)

        texto_inicial = f"${self.saldo_inicial:.2f}" if self.saldo_inicial > 0 else "--"
        self.lbl_inicial = tk.Label(self.metrics_frame, text=f"[S] Inicial: {texto_inicial}", bg=self.bg_frame, fg=self.accent_blue, font=("Segoe UI", 11, "bold"), width=25, anchor="w")
        self.lbl_inicial.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.lbl_atual = tk.Label(self.metrics_frame, text="[$] Atual: --", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 11, "bold"), width=25, anchor="w")
        self.lbl_atual.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        self.lbl_pl = tk.Label(self.metrics_frame, text="[%] P/L Total: --", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 11, "bold"), width=30, anchor="w")
        self.lbl_pl.grid(row=0, column=2, padx=10, pady=5, sticky="w")

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

            self.lbl_det_atu = tk.Label(self.metrics_frame, text="Análise: Aguardando...", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 10), width=130, anchor="w")
            self.lbl_det_atu.grid(row=5, column=1, columnspan=3, padx=10, pady=5, sticky="w")
            
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

        tk.Label(self.right_panel, text="🟢 TENDÊNCIA DE ALTA", bg=self.bg_frame, fg=self.accent_green, font=("Segoe UI", 9, "bold")).pack(pady=(10,5))
        self.list_hot = tk.Listbox(self.right_panel, bg="#000000", fg=self.neutral_obs, font=("Consolas", 9), selectbackground="#3c4043", highlightthickness=0, borderwidth=0)
        self.list_hot.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

        tk.Label(self.right_panel, text="❄️ TENDÊNCIA DE BAIXA", bg=self.bg_frame, fg=self.geladeira_dark, font=("Segoe UI", 9, "bold")).pack(pady=(5,5))
        self.list_cold = tk.Listbox(self.right_panel, bg="#000000", fg=self.geladeira_dark, font=("Consolas", 9), selectbackground="#3c4043", highlightthickness=0, borderwidth=0)
        self.list_cold.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

        self.process = None
        self.bot_running = False

    def _load_gui_state(self):
        if os.path.exists(self.gui_state_file):
            try:
                with open(self.gui_state_file, "r") as file_handler:
                    state_data = json.load(file_handler)
                    self.saldo_inicial = state_data.get("saldo_inicial", 0.0)
            except: pass

    def _save_gui_state(self):
        try:
            with open(self.gui_state_file, "w") as file_handler:
                json.dump({"saldo_inicial": self.saldo_inicial}, file_handler)
        except: pass

    def reset_initial_balance(self):
        if self.saldo_atual > 0:
            self.saldo_inicial = self.saldo_atual
            self._save_gui_state()
            self.lbl_inicial.config(text=f"[S] Inicial: ${self.saldo_inicial:.2f}")
            self.log_message("\n[✓] ♻️ Saldo Inicial sincronizado com sucesso!\n")

    def reset_scoreboard(self):
        try:
            # 1. Cria a flag para o motor do bot (sincronização de backend)
            with open("reset_trades.flag", "w") as f:
                f.write("reset")
            
            # 2. Atualização imediata do painel visual
            self.lbl_trades.config(text="TRADES: 0 | W: 0 | L: 0 (0.0%)")
            
            # 3. Limpeza do JSON temporário para o loop do painel não buscar dados velhos
            if os.path.exists("bot_status.json"):
                with open("bot_status.json", "r", encoding="utf-8") as f:
                    state_data = json.load(f)
                state_data["trades_won"] = 0
                state_data["trades_lost"] = 0
                with open("bot_status.json", "w", encoding="utf-8") as f:
                    json.dump(state_data, f, ensure_ascii=False, indent=2)

            # 4. Limpeza do arquivo de memória do motor (útil se o bot estiver parado no momento)
            if os.path.exists("profit_gain_state.json"):
                with open("profit_gain_state.json", "r") as f:
                    pg_state = json.load(f)
                pg_state["trades_won"] = 0
                pg_state["trades_lost"] = 0
                with open("profit_gain_state.json", "w") as f:
                    json.dump(pg_state, f)

            self.log_message("\n[✓] ♻️ Placar de trades zerado com sucesso!\n")
        except Exception as e:
            self.log_message(f"\n[X] Erro ao zerar placar: {e}\n")

    def draw_mini_chart(self, chart_data_points, coin_symbol, buy_price_value=0.0, buy_time_stamp=0.0):
        self.canvas_chart.delete("all")
        if not chart_data_points or len(chart_data_points) < 2:
            self.lbl_chart_title.config(text=f"{coin_symbol} - Aguardando Dados...")
            return

        self.lbl_chart_title.config(text=f"{coin_symbol} - Últimas 2h30 (5m)", fg=self.accent_blue)
        
        canvas_width = int(self.canvas_chart['width'])
        canvas_height = int(self.canvas_chart['height'])
        padding_value = 5
        
        min_chart_value = min(chart_data_points)
        max_chart_value = max(chart_data_points)
        value_range = max_chart_value - min_chart_value if max_chart_value != min_chart_value else 1
        
        line_color = self.accent_green if chart_data_points[-1] >= chart_data_points[0] else self.accent_red
        
        plotted_points = []
        x_axis_step = (canvas_width - 2*padding_value) / (len(chart_data_points) - 1)
        for index, current_value in enumerate(chart_data_points):
            x_coordinate = padding_value + index * x_axis_step
            y_coordinate = padding_value + (canvas_height - 2*padding_value) * (1 - (current_value - min_chart_value) / value_range)
            plotted_points.append(x_coordinate)
            plotted_points.append(y_coordinate)
            
        self.canvas_chart.create_line(plotted_points, fill=line_color, width=2, smooth=True)

        if buy_price_value > 0 and (min_chart_value <= buy_price_value <= max_chart_value):
            y_buy_coordinate = padding_value + (canvas_height - 2*padding_value) * (1 - (buy_price_value - min_chart_value) / value_range)
            self.canvas_chart.create_line(padding_value, y_buy_coordinate, canvas_width-padding_value, y_buy_coordinate, fill="#f2a900", dash=(2, 2))
            if buy_time_stamp > 0:
                diff_seconds = time.time() - buy_time_stamp
                candles_ago_count = diff_seconds / 300.0 
                idx_compra_plot = (len(chart_data_points) - 1) - candles_ago_count
                if 0 <= idx_compra_plot <= len(chart_data_points) - 1:
                    x_buy_coordinate = padding_value + idx_compra_plot * x_axis_step
                    circle_radius = 3
                    self.canvas_chart.create_oval(x_buy_coordinate-circle_radius, y_buy_coordinate-circle_radius, x_buy_coordinate+circle_radius, y_buy_coordinate+circle_radius, fill="#f2a900", outline="#ffffff", width=1)

    def check_bot_state_json(self):
        if self.bot_running and os.path.exists("bot_status.json"):
            try:
                with open("bot_status.json", "r", encoding="utf-8") as file_handler:
                    state_data = json.load(file_handler)
                
                if state_data:
                    if self.current_strategy == 'profit_gain':
                        if "coin" in state_data:
                            coin_symbol = state_data.get('coin', 'BUSCANDO...')
                            self.lbl_cur_coin.config(text=f"Current Coin: {coin_symbol}")
                            
                            btc_price_value = state_data.get('btc_price', 0.0)
                            btc_change_value = state_data.get('btc_change', 0.0)
                            cor_texto_btc = self.accent_green if btc_change_value >= 0 else self.accent_red
                            self.lbl_btc.config(text=f"BTC: ${btc_price_value:,.2f} | Var: {btc_change_value:+.2f}%", fg=cor_texto_btc)
                            
                            buy_price_value = state_data.get('buy_price', 0.0)
                            current_price_value = state_data.get('current_price', 0.0)
                            target_price_value = state_data.get('target_price', 0.0)
                            active_quantity = state_data.get('active_qty', 0.0)
                            buy_time_stamp = state_data.get('buy_time', 0.0)
                            
                            if buy_price_value > 0 and active_quantity > 0:
                                total_buy_usdt = buy_price_value * active_quantity
                                total_current_usdt = current_price_value * active_quantity
                                total_target_usdt = target_price_value * active_quantity
                                self.lbl_buy_price.config(text=f"[🛒] Compra Est.: ${buy_price_value:.6f}   |   {total_buy_usdt:.2f} USDT ⇌ {active_quantity:.4f} {coin_symbol}")
                                self.lbl_cur_price.config(text=f"[💲] Atual: ${current_price_value:.6f}   |   {total_current_usdt:.2f} USDT ⇌ {active_quantity:.4f} {coin_symbol}")
                                self.lbl_tgt_price.config(text=f"[🎯] Alvo (Venda): ${target_price_value:.6f}   |   {total_target_usdt:.2f} USDT ⇌ {active_quantity:.4f} {coin_symbol}")
                            else:
                                self.lbl_buy_price.config(text="[🛒] Compra Est.: --")
                                self.lbl_cur_price.config(text="[💲] Atual: --")
                                self.lbl_tgt_price.config(text="[🎯] Alvo (Venda): --")
                                
                            self.lbl_det_atu.config(text=f"{state_data.get('detalhe_atual', '--')}")
                            
                            trades_won_count = state_data.get("trades_won", 0)
                            trades_lost_count = state_data.get("trades_lost", 0)
                            total_trades_count = trades_won_count + trades_lost_count
                            win_rate_percentage = (trades_won_count / total_trades_count * 100) if total_trades_count > 0 else 0.0
                            self.lbl_trades.config(text=f"TRADES: {total_trades_count} | W: {trades_won_count} | L: {trades_lost_count} ({win_rate_percentage:.1f}%)")
                            
                            if "status" in state_data:
                                cor_texto_status = self.accent_yellow if "Em Operação" in state_data['status'] else self.accent_blue
                                if "Crash" in state_data['status']: cor_texto_status = self.accent_red
                                self.lbl_status.config(text=f"STATUS: {state_data['status']}", fg=cor_texto_status)
                            
                            chart_data_points = state_data.get('chart_data', [])
                            if chart_data_points:
                                self.draw_mini_chart(chart_data_points, coin_symbol, buy_price_value, buy_time_stamp)
                            else:
                                self.canvas_chart.delete("all")
                                self.lbl_chart_title.config(text="Mini-Gráfico (Inativo)", fg="#9aa0a6")

                            aptas_list = state_data.get('aptas', [])
                            geladeira_list = state_data.get('geladeira', [])
                            
                            self.list_hot.delete(0, tk.END)
                            for item in aptas_list: self.list_hot.insert(tk.END, item)
                            
                            self.list_cold.delete(0, tk.END)
                            for item in geladeira_list: self.list_cold.insert(tk.END, item)
                            
                    else:
                        if "coin" in state_data:
                            self.lbl_cur_coin.config(text=f"Current Coin: {state_data.get('coin', 'BUSCANDO...')}")
                            self.lbl_last_jump.config(text=f"Último Salto: {state_data.get('last_jump', 'Nenhum')}")
                            
                            btc_price_value = state_data.get('btc_price', 0.0)
                            btc_change_value = state_data.get('btc_change', 0.0)
                            cor_texto_btc = self.accent_green if btc_change_value >= 0 else self.accent_red
                            self.lbl_btc.config(text=f"BTC: ${btc_price_value:,.2f} | Var: {btc_change_value:+.2f}%", fg=cor_texto_btc)
                            
                            self.lbl_rota.config(text=f"Rota: {state_data.get('route', 'Analisando...')}")
                            
                            if "status" in state_data:
                                cor_texto_status = self.accent_yellow if "Segurando" in state_data['status'] else self.accent_blue
                                if "Crash" in state_data['status']: cor_texto_status = self.accent_red
                                self.lbl_status.config(text=f"STATUS: {state_data['status']}", fg=cor_texto_status)

                            prev_coin_symbol = state_data.get('prev_coin', 'Nenhuma')
                            prev_quantity = state_data.get('prev_qty', 0.0)
                            prev_sell_quantity = state_data.get('prev_sell', 0.0)
                            prev_dust_amount = state_data.get('prev_dust', 0.0)
                            
                            if prev_coin_symbol in ["Nenhuma", "USDT"]:
                                self.lbl_qtd_prev.config(text=f"[⏪] Anterior ({prev_coin_symbol}): -- | Venda Real: -- | Poeira: --", fg="#9aa0a6")
                            else:
                                self.lbl_qtd_prev.config(text=f"[⏪] Anterior ({prev_coin_symbol}): {prev_quantity:.4f} | Venda Real: {prev_sell_quantity:.4f} | Poeira: {prev_dust_amount:.4f}", fg="#9aa0a6")
                            
                            current_coin_symbol = state_data.get('coin', 'BUSCANDO...')
                            current_quantity = state_data.get('current_qty', 0.0)
                            sell_quantity = state_data.get('sell_qty', 0.0)
                            dust_amount = state_data.get('dust', 0.0)

                            if current_quantity == 0.0:
                                self.lbl_qtd.config(text=f"[📦] Atual ({current_coin_symbol}): -- | Venda Real: -- | Poeira: --", fg=self.fg_text)
                            else:
                                self.lbl_qtd.config(text=f"[📦] Atual ({current_coin_symbol}): {current_quantity:.4f} | Venda Real: {sell_quantity:.4f} | Poeira: {dust_amount:.4f}", fg=self.accent_green)

                            initial_balance_value = state_data.get("init_bal", 0.0)
                            peak_profit_value = state_data.get("peak_profit", 0.0)
                            current_profit_value = state_data.get("curr_profit", 0.0)
                            target_profit_value = state_data.get("global_tp", 3.5)
                            trailing_drop_value = state_data.get("trailing_drop", 0.4)

                            if initial_balance_value > 0:
                                if peak_profit_value > 0:
                                    self.lbl_trailing.config(text=f"🎯 Trailing [ATIVO]: Gatilho {target_profit_value}% | Pico: {peak_profit_value:.2f}% | Atual: {current_profit_value:.2f}% (Vende se recuar {trailing_drop_value}%)", fg=self.accent_green)
                                else:
                                    self.lbl_trailing.config(text=f"🎯 Meta Global: Gatilho em {target_profit_value}% | Lucro Atual: {current_profit_value:.2f}%", fg=self.accent_yellow)
                            else:
                                self.lbl_trailing.config(text="🎯 Meta Global: Calculando saldo base...", fg=self.fg_text)

                            hot_coins_list = state_data.get('hot_coins', [])
                            cold_coins_list = state_data.get('cold_coins', [])
                            self.list_hot.delete(0, tk.END)
                            for item in hot_coins_list: self.list_hot.insert(tk.END, item)
                            self.list_cold.delete(0, tk.END)
                            for item in cold_coins_list: self.list_cold.insert(tk.END, item)

            except Exception: pass 
                
        self.root.after(2000, self.check_bot_state_json)

    def read_output(self):
        if self.process:
            for log_line in iter(self.process.stdout.readline, ''):
                self.log_message(log_line)
            
            self.process.stdout.close()
            self.process.wait()
            
            if self.bot_running:
                self.root.after(0, lambda: self.lbl_status.config(text="STATUS: Erro/Crash (Veja o Log)", fg=self.accent_red))
                self.bot_running = False

    def get_total_usdt_balance(self, binance_client_instance, bridge_symbol):
        try:
            account_data = binance_client_instance.get_account()
            ticker_dictionary = {ticker_info['symbol']: float(ticker_info['price']) for ticker_info in binance_client_instance.get_symbol_ticker()}
            total_usdt_value = 0.0
            for balance_info in account_data['balances']:
                free_balance = float(balance_info['free']) + float(balance_info['locked'])
                if free_balance > 0:
                    asset_symbol = balance_info['asset']
                    if asset_symbol == bridge_symbol: total_usdt_value += free_balance
                    else:
                        market_symbol = f"{asset_symbol}{bridge_symbol}"
                        if market_symbol in ticker_dictionary: total_usdt_value += free_balance * ticker_dictionary[market_symbol]
            return total_usdt_value
        except: return 0.0

    def update_stats_loop(self):
        try:
            config_instance = Config()
            binance_client_instance = Client(config_instance.BINANCE_API_KEY, config_instance.BINANCE_API_SECRET_KEY, tld=config_instance.BINANCE_TLD)
            bridge_symbol = config_instance.BRIDGE.symbol if hasattr(config_instance.BRIDGE, 'symbol') else getattr(config_instance, 'BRIDGE', 'USDT')
            
            for _ in range(3):
                start_time = time.time()
                total_atual_value = self.get_total_usdt_balance(binance_client_instance, bridge_symbol)
                ping_latency_ms = int((time.time() - start_time) * 1000)
                if total_atual_value > 0:
                    self.saldo_atual = total_atual_value
                    if self.saldo_inicial == 0.0:
                        self.saldo_inicial = total_atual_value
                        self._save_gui_state()
                        
                    self.root.after(0, lambda u=self.saldo_inicial, p=ping_latency_ms: [
                        self.lbl_inicial.config(text=f"[S] Inicial: ${u:.2f}"),
                        self.lbl_ping.config(text=f"PING: {p} ms")
                    ])
                    break
                time.sleep(1)
            
            while self.bot_running:
                start_time = time.time()
                total_atual_value = self.get_total_usdt_balance(binance_client_instance, bridge_symbol)
                ping_latency_ms = int((time.time() - start_time) * 1000)
                
                if total_atual_value > 0:
                    self.saldo_atual = total_atual_value
                    
                if self.saldo_inicial > 0 and total_atual_value > 0:
                    profit_loss_value = total_atual_value - self.saldo_inicial
                    profit_loss_percentage = (profit_loss_value / self.saldo_inicial) * 100
                    cor_texto_pl = self.accent_green if profit_loss_value >= 0 else self.accent_red
                else:
                    profit_loss_value = profit_loss_percentage = 0
                    cor_texto_pl = self.fg_text

                if total_atual_value > 0:
                    self.root.after(0, lambda a=total_atual_value, p=profit_loss_value, pp=profit_loss_percentage, c=cor_texto_pl, pi=ping_latency_ms: [
                        self.lbl_atual.config(text=f"[$] Atual: ${a:.2f}"),
                        self.lbl_pl.config(text=f"[%] P/L Total: ${p:.2f} ({pp:.2f}%)", fg=c),
                        self.lbl_ping.config(text=f"PING: {pi} ms")
                    ])
                time.sleep(15)
        except: pass

    def start_bot(self):
        self.log_message("[!] Iniciando...\n")
        self.lbl_status.config(text="STATUS: Booting...", fg=self.fg_text)
        with open("bot_status.json", "w") as file_handler: json.dump({}, file_handler)
        
        environment_variables = os.environ.copy()
        environment_variables["PYTHONIOENCODING"] = "utf-8"
        self.bot_running = True
        self.process = subprocess.Popen(
            [sys.executable, "-m", "binance_trade_bot"], 
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding='utf-8', errors='replace', env=environment_variables
        )
        threading.Thread(target=self.read_output, daemon=True).start()
        threading.Thread(target=self.update_stats_loop, daemon=True).start()
        self.check_bot_state_json()

    def stop_bot(self):
        if self.process: self.process.terminate()
        self.bot_running = False
        self.lbl_status.config(text="STATUS: Parado", fg=self.fg_text)

    def clear_log(self): self.log_area.delete(1.0, tk.END)

    def log_message(self, message_text):
        def _append_and_clean():
            self.log_area.insert(tk.END, message_text)
            self.log_area.yview(tk.END)
            total_linhas_log = int(self.log_area.index('end-1c').split('.')[0])
            if total_linhas_log > 1500: self.log_area.delete('1.0', '500.0')
        self.root.after(0, _append_and_clean)


if __name__ == "__main__":
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

    root_window = tk.Tk()
    app_instance = BinanceBotGUI(root_window)
    root_window.mainloop()