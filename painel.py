import tkinter as tk
from tkinter import scrolledtext
import tkinter.messagebox as messagebox
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
        self.root.geometry("1200x800")
        
        try:
            self.root.state('zoomed')
        except Exception:
            pass
        
        try:
            self.bot_config = Config()
            self.current_strategy = getattr(self.bot_config, 'STRATEGY', 'default').lower()
        except Exception:
            self.current_strategy = 'default'
            
        self.gui_state_file = "gui_state.json"
        self.initial_balance = 0.0
        self.current_balance = 0.0
        self.locked_at_trade_count = -1
        self.in_operation = False
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

        self.tools_frame = tk.Frame(root, bg=self.bg_main, pady=5)
        self.tools_frame.pack(fill=tk.X, side=tk.TOP, padx=15)
        
        self.btn_ai = tk.Button(self.tools_frame, text="🧠 Ver Análise da IA", command=self.show_ai_analysis, bg="#2b3139", fg=self.neutral_obs, font=("Segoe UI", 9, "bold"), width=20)
        self.btn_ai.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_hist = tk.Button(self.tools_frame, text="📜 Histórico do Dia", command=self.show_daily_history, bg="#2b3139", fg=self.neutral_obs, font=("Segoe UI", 9, "bold"), width=20)
        self.btn_hist.pack(side=tk.LEFT, padx=5)
        
        self.btn_add_trade = tk.Button(self.tools_frame, text="🔋 +1 Tentativa Hoje", command=self.add_trade_chance, bg=self.accent_green, fg="black", font=("Segoe UI", 9, "bold"), width=20)
        self.btn_add_trade.pack(side=tk.RIGHT, padx=0)
        
        self.btn_force_sell = tk.Button(self.tools_frame, text="🚨 Venda Forçada", command=self.force_sell_action, bg=self.accent_red, fg="white", font=("Segoe UI", 9, "bold"), width=18)
        self.btn_force_sell.pack(side=tk.RIGHT, padx=5)

        self.btn_update = tk.Button(self.tools_frame, text="🔄 Atualizar Versão", command=self.request_update, bg=self.accent_blue, fg="black", font=("Segoe UI", 9, "bold"), width=20)
        self.btn_update.pack(side=tk.RIGHT, padx=5)
        
        self.metrics_frame = tk.Frame(root, bg=self.bg_frame, pady=15)
        self.metrics_frame.pack(fill=tk.X, side=tk.TOP, padx=15, pady=10)

        self.metrics_frame.columnconfigure(0, weight=1)
        self.metrics_frame.columnconfigure(1, weight=2) 
        self.metrics_frame.columnconfigure(2, weight=1)
        self.metrics_frame.columnconfigure(3, weight=0)

        texto_inicial = f"${self.initial_balance:.2f}" if self.initial_balance > 0 else "--"
        self.lbl_inicial = tk.Label(self.metrics_frame, text=f"[S] Saldo Inicial: {texto_inicial}", bg=self.bg_frame, fg=self.accent_blue, font=("Segoe UI", 10, "bold"), anchor="w")
        self.lbl_inicial.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        
        self.lbl_atual = tk.Label(self.metrics_frame, text="[$] Saldo Atual: --", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 10, "bold"), anchor="w")
        self.lbl_atual.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        
        self.lbl_pl = tk.Label(self.metrics_frame, text="P/L Total: --", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 10, "bold"), anchor="w")
        self.lbl_pl.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        
        self.lbl_trades = tk.Label(self.metrics_frame, text="TRADES: 0 | W: 0 | L: 0 (0.0%)", bg=self.bg_frame, fg=self.accent_yellow, font=("Segoe UI", 10, "bold"), anchor="w")
        self.lbl_trades.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        
        self.lbl_status = tk.Label(self.metrics_frame, text="STATUS: Aguardando...", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 10, "bold"), anchor="w")
        self.lbl_status.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w")

        self.lbl_btc = tk.Label(self.metrics_frame, text="BTC: Buscando...", bg=self.bg_frame, fg=self.btc_gold, font=("Segoe UI", 10, "bold"), anchor="w")
        self.lbl_btc.grid(row=0, column=1, padx=10, pady=5, sticky="w")
        
        if self.current_strategy == 'profit_gain':
            self.lbl_buy_price = tk.Label(self.metrics_frame, text="[🛒] Compra Est.: $0.000000 | 0.00 USDT ⇌ 0.0000", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 10, "bold"), anchor="w")
            self.lbl_buy_price.grid(row=1, column=1, padx=10, pady=5, sticky="w")
            
            self.lbl_cur_price = tk.Label(self.metrics_frame, text="[💲] Atual: $0.000000 | 0.00 USDT ⇌ 0.0000", bg=self.bg_frame, fg=self.accent_blue, font=("Segoe UI", 10, "bold"), anchor="w")
            self.lbl_cur_price.grid(row=2, column=1, padx=10, pady=5, sticky="w")
            
            self.lbl_tgt_price = tk.Label(self.metrics_frame, text="[🎯] Alvo (Venda): $0.000000 | 0.00 USDT ⇌ 0.0000", bg=self.bg_frame, fg=self.accent_green, font=("Segoe UI", 10, "bold"), anchor="w")
            self.lbl_tgt_price.grid(row=3, column=1, padx=10, pady=5, sticky="w")

        self.lbl_cur_coin = tk.Label(self.metrics_frame, text="Current Coin: BUSCANDO...", bg=self.bg_frame, fg=self.accent_blue, font=("Segoe UI", 10, "bold"), anchor="w")
        self.lbl_cur_coin.grid(row=0, column=2, padx=10, pady=5, sticky="w")
        
        self.lbl_ping = tk.Label(self.metrics_frame, text="PING: -- ms", bg=self.bg_frame, fg="#bdc1c6", font=("Segoe UI", 10), anchor="w")
        self.lbl_ping.grid(row=1, column=2, padx=10, pady=5, sticky="w")
        
        self.lbl_heartbeat = tk.Label(self.metrics_frame, text="💓 Última batida: --", bg=self.bg_frame, fg="#bdc1c6", font=("Segoe UI", 10, "bold"), anchor="w")
        self.lbl_heartbeat.grid(row=2, column=2, padx=10, pady=5, sticky="w")
        
        self.lbl_countdown = tk.Label(self.metrics_frame, text="⏳ Próxima Análise: --", bg=self.bg_frame, fg=self.accent_yellow, font=("Segoe UI", 10, "bold"), anchor="w")
        self.lbl_countdown.grid(row=3, column=2, padx=10, pady=5, sticky="w")
        
        if self.current_strategy == 'profit_gain':
            self.canvas_chart = tk.Canvas(self.metrics_frame, bg="#000000", width=280, height=110, highlightthickness=1, highlightbackground="#3c4043")
            self.canvas_chart.grid(row=0, column=3, rowspan=4, padx=(0,10), pady=5, sticky="e")
            self.lbl_chart_title = tk.Label(self.metrics_frame, text="Mini-Gráfico (Inativo)", bg=self.bg_frame, fg="#9aa0a6", font=("Segoe UI", 8, "bold"))
            self.lbl_chart_title.grid(row=4, column=3, sticky="e", padx=(0,10))

        self.lbl_det_atu = tk.Label(self.metrics_frame, text="Aguardando detalhes da operação...", bg=self.bg_frame, fg=self.fg_text, font=("Segoe UI", 10), anchor="w", justify="left")
        self.lbl_det_atu.grid(row=5, column=0, columnspan=4, padx=10, pady=(10, 5), sticky="we")

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
                    self.initial_balance = state_data.get("saldo_inicial", 0.0)
            except: pass

    def _save_gui_state(self):
        try:
            with open(self.gui_state_file, "w") as file_handler:
                json.dump({"saldo_inicial": self.initial_balance}, file_handler)
        except: pass

    def request_update(self):
        """ Inicializa a verificação de update remoto. Bloqueia execução imediata caso o motor opere capital em risco. """
        if self.in_operation:
            with open("update_pending.flag", "w") as flag_file:
                flag_file.write("pending")
            self.btn_update.config(state=tk.DISABLED, text="⏳ Aguardando Venda...")
            self.log_message("\n[INFO] Atualização agendada para execução pós-venda.\n")
        else:
            self.perform_update()

    def perform_update(self):
        """ Processa a sincronização silenciosa via Git e invoca auto-restart estrutural se houver alterações. """
        self.btn_update.config(state=tk.DISABLED, text="Baixando atualização...")
        self.log_message("\n[INFO] Estabelecendo conexão com repositório remoto...\n")
        
        was_running = self.bot_running
        try:
            self.stop_bot()
            subprocess.run(["git", "reset", "--hard", "HEAD"], capture_output=True, text=True, timeout=10)
            result = subprocess.run(["git", "pull"], capture_output=True, text=True, timeout=15)

            if "Already up to date." in result.stdout or "Already up-to-date." in result.stdout:
                self.log_message("[OK] Sistema encontra-se na versão mais recente.\n")
                if os.path.exists("update_pending.flag"): os.remove("update_pending.flag")
                self.btn_update.config(state=tk.NORMAL, text="🔄 Atualizar Versão")
                if was_running:
                    self.start_bot()
            elif result.returncode == 0:
                self.log_message("[OK] Atualização validada. Reiniciando interface do usuário...\n")
                if os.path.exists("update_pending.flag"): os.remove("update_pending.flag")
                time.sleep(2)
                
                script_absolute_path = os.path.abspath(sys.argv[0])
                subprocess.Popen([sys.executable, script_absolute_path])
                self.root.quit()
                sys.exit()
            else:
                self.log_message("[ERROR] Conflito de integridade com o tracking remoto.\n")
                if os.path.exists("update_pending.flag"): os.remove("update_pending.flag")
                self.btn_update.config(state=tk.NORMAL, text="🔄 Atualizar Versão")
                if was_running:
                    self.start_bot()
        except Exception as exception_log:
            self.log_message(f"[ERROR] Exceção gerada durante o protocolo de sub-processo: {exception_log}\n")
            if os.path.exists("update_pending.flag"): os.remove("update_pending.flag")
            self.btn_update.config(state=tk.NORMAL, text="🔄 Atualizar Versão")
            if was_running:
                self.start_bot()

    def add_trade_chance(self):
        with open("add_trade.flag", "w") as f:
            f.write("1")
        self.btn_add_trade.config(state=tk.DISABLED, bg="#5f6368")
        current_trades = 0
        if os.path.exists("bot_status.json"):
            try:
                with open("bot_status.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    current_trades = data.get("daily_trades", 0)
            except Exception: pass
        self.locked_at_trade_count = current_trades
        self.log_message("\n[+] Extensão de limite de operações solicitada ao motor central.\n")

    def force_sell_action(self):
        resposta = messagebox.askyesno(
            "ATENÇÃO: VENDA FORÇADA", 
            "Confirma o encerramento manual e imediato da operação financeira vigente?\n\nO algoritmo consolidará o resultado a mercado e efetuará pausa compulsória de 60 segundos."
        )
        if resposta:
            try:
                with open("force_sell.flag", "w") as f:
                    f.write("trigger_manual_sell")
                self.log_message("\n[INFO] Diretiva de venda interceptada. Aguardando execução do motor.\n")
            except Exception as flag_error:
                self.log_message(f"\n[ERROR] Falha na emissão do comando: {flag_error}\n")

    def show_ai_analysis(self):
        top = tk.Toplevel(self.root)
        top.title("Parecer Analítico Institucional")
        top.geometry("700x450")
        top.configure(bg=self.bg_frame)
        top.transient(self.root) 
        top.grab_set() 

        lbl = tk.Label(top, text="Dossiê Quantitativo", bg=self.bg_frame, fg=self.accent_yellow, font=("Segoe UI", 12, "bold"))
        lbl.pack(pady=(15, 5))

        txt = scrolledtext.ScrolledText(top, wrap=tk.WORD, bg="#000000", fg=self.accent_green, font=("Consolas", 10))
        txt.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        report = getattr(self, 'current_ai_report', "Nenhum relatório foi processado neste ciclo.")
        txt.insert(tk.END, report)
        txt.config(state=tk.DISABLED)

    def show_daily_history(self):
        top = tk.Toplevel(self.root)
        top.title("Extrato de Operações")
        top.geometry("600x350")
        top.configure(bg=self.bg_frame)
        top.transient(self.root)
        top.grab_set()

        lbl = tk.Label(top, text="Histórico Financeiro Diário", bg=self.bg_frame, fg=self.accent_blue, font=("Segoe UI", 12, "bold"))
        lbl.pack(pady=(15, 5))

        txt = scrolledtext.ScrolledText(top, wrap=tk.WORD, bg="#000000", fg=self.fg_text, font=("Consolas", 10))
        txt.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        hist = getattr(self, 'current_daily_history', [])
        if not hist:
            txt.insert(tk.END, "Nenhuma transação registrada na data vigente.")
        else:
            for item in hist:
                cor_res = "🟢" if "+" in item['result'] else "🔴"
                linha = f"[{item['time']}] {cor_res} {item['coin']: <8} -> {item['result']} (Motivo de saída: {item['reason']})\n\n"
                txt.insert(tk.END, linha)
        txt.config(state=tk.DISABLED)

    def reset_initial_balance(self):
        if self.current_balance > 0:
            self.initial_balance = self.current_balance
            self._save_gui_state()
            self.lbl_inicial.config(text=f"[S] Saldo Inicial: ${self.initial_balance:.2f}")
            self.log_message("\n[OK] Capital inicial recalibrado com sucesso.\n")

    def reset_scoreboard(self):
        try:
            with open("reset_trades.flag", "w") as f:
                f.write("reset")
            
            self.lbl_trades.config(text="TRADES: 0 | W: 0 | L: 0 (0.0%)")
            
            if os.path.exists("bot_status.json"):
                with open("bot_status.json", "r", encoding="utf-8") as f:
                    state_data = json.load(f)
                state_data["trades_won"] = 0
                state_data["trades_lost"] = 0
                with open("bot_status.json", "w", encoding="utf-8") as f:
                    json.dump(state_data, f, ensure_ascii=False, indent=2)

            if os.path.exists("profit_gain_state.json"):
                with open("profit_gain_state.json", "r") as f:
                    pg_state = json.load(f)
                pg_state["trades_won"] = 0
                pg_state["trades_lost"] = 0
                with open("profit_gain_state.json", "w") as f:
                    json.dump(pg_state, f)

            self.log_message("\n[OK] Placar financeiro e estatísticas reiniciados.\n")
        except Exception as file_error:
            self.log_message(f"\n[ERROR] Falha ao sobreescrever persistência de placar: {file_error}\n")

    def draw_mini_chart(self, chart_data_points, coin_symbol, buy_price_value=0.0, buy_time_stamp=0.0):
        self.canvas_chart.delete("all")
        if not chart_data_points or len(chart_data_points) < 2:
            self.lbl_chart_title.config(text=f"{coin_symbol} - Formando dados...")
            return

        self.lbl_chart_title.config(text=f"{coin_symbol} - Últimas 7h30 (15m)", fg=self.accent_blue)
        
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
                candles_ago_count = diff_seconds / 900.0 
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
                        
                        self.current_ai_report = state_data.get("full_ai_report", "Aguardando dados estruturados...")
                        self.current_daily_history = state_data.get("daily_history", [])
                        trades_no_dia = state_data.get("daily_trades", 0)
                        
                        self.in_operation = "Em Operação" in state_data.get("status", "")
                        
                        if os.path.exists("update_pending.flag"):
                            self.btn_update.config(state=tk.DISABLED, text="⏳ Aguardando Venda...")
                            if not self.in_operation:
                                self.perform_update()

                        if self.btn_add_trade['state'] == tk.DISABLED:
                            if not self.in_operation and trades_no_dia > self.locked_at_trade_count:
                                self.btn_add_trade.config(state=tk.NORMAL, bg=self.accent_green)
                        
                        cooldown_until = state_data.get('cooldown_until', 0.0)
                        if not self.in_operation:
                            if time.time() < cooldown_until:
                                restante = int(cooldown_until - time.time())
                                mins, secs = divmod(restante, 60)
                                self.lbl_countdown.config(text=f"⏳ Próxima Análise: {mins:02d}:{secs:02d}")
                            else:
                                self.lbl_countdown.config(text="⏳ Próxima Análise: Executando...")
                        else:
                            self.lbl_countdown.config(text="⏳ Próxima Análise: -- (Em operação)")
                        
                        last_hb_ts = state_data.get("last_heartbeat_ts", 0.0)
                        if last_hb_ts > 0:
                            delta_hb = time.time() - last_hb_ts
                            cor_hb = self.accent_green if delta_hb <= 80 else (self.accent_yellow if delta_hb <= 300 else self.accent_red)
                            hb_str = time.strftime("%H:%M:%S", time.localtime(last_hb_ts))
                            self.lbl_heartbeat.config(text=f"💓 Última batida: {hb_str}", fg=cor_hb)
                        
                        if "coin" in state_data:
                            coin_symbol = state_data.get('coin', 'BUSCANDO...')
                            coin_change = state_data.get('current_coin_change', 0.0)
                            current_price_value = state_data.get('current_price', 0.0)
                            
                            if coin_symbol in ["USDT", "BTC"] or not self.in_operation:
                                self.lbl_cur_coin.config(text=f"Current Coin: {coin_symbol}")
                            else:
                                self.lbl_cur_coin.config(text=f"Current Coin: {coin_symbol} | ${current_price_value:.4f} | Var: {coin_change:+.2f}%")
                            
                            btc_price_value = state_data.get('btc_price', 0.0)
                            btc_change_value = state_data.get('btc_change', 0.0)
                            cor_texto_btc = self.accent_green if btc_change_value >= 0 else self.accent_red
                            self.lbl_btc.config(text=f"BTC: ${btc_price_value:,.2f} | Var: {btc_change_value:+.2f}%", fg=cor_texto_btc)
                            
                            buy_price_value = state_data.get('buy_price', 0.0)
                            target_price_value = state_data.get('target_price', 0.0)
                            active_quantity = state_data.get('active_qty', 0.0)
                            buy_time_stamp = state_data.get('buy_time', 0.0)
                            
                            if buy_price_value > 0 and active_quantity > 0:
                                total_buy_usdt = buy_price_value * active_quantity
                                total_current_usdt = current_price_value * active_quantity
                                total_target_usdt = target_price_value * active_quantity
                                self.lbl_buy_price.config(text=f"[🛒] Compra Est.: ${buy_price_value:.6f} | {total_buy_usdt:.2f} USDT ⇌ {active_quantity:.4f} {coin_symbol}")
                                self.lbl_cur_price.config(text=f"[💲] Atual: ${current_price_value:.6f} | {total_current_usdt:.2f} USDT ⇌ {active_quantity:.4f} {coin_symbol}")
                                self.lbl_tgt_price.config(text=f"[🎯] Alvo (Venda): ${target_price_value:.6f} | {total_target_usdt:.2f} USDT ⇌ {active_quantity:.4f} {coin_symbol}")
                            else:
                                self.lbl_buy_price.config(text=f"[🛒] Compra Est.: $0.000000 | 0.00 USDT ⇌ 0.0000")
                                self.lbl_cur_price.config(text=f"[💲] Atual: $0.000000 | 0.00 USDT ⇌ 0.0000")
                                self.lbl_tgt_price.config(text=f"[🎯] Alvo (Venda): $0.000000 | 0.00 USDT ⇌ 0.0000")
                                
                            self.lbl_det_atu.config(text=f"{state_data.get('current_detail', '--')}")
                            
                            trades_won_count = state_data.get("trades_won", 0)
                            trades_lost_count = state_data.get("trades_lost", 0)
                            total_trades_count = trades_won_count + trades_lost_count
                            win_rate_percentage = (trades_won_count / total_trades_count * 100) if total_trades_count > 0 else 0.0
                            self.lbl_trades.config(text=f"TRADES: {total_trades_count} | W: {trades_won_count} | L: {trades_lost_count} ({win_rate_percentage:.1f}%)")
                            
                            if "status" in state_data:
                                cor_texto_status = self.accent_yellow if "Em Operação" in state_data['status'] else self.accent_blue
                                if "Crash" in state_data['status'] or "⚠️" in state_data['status']: cor_texto_status = self.accent_red
                                self.lbl_status.config(text=f"STATUS: {state_data['status']}", fg=cor_texto_status)
                            
                            chart_data_points = state_data.get('chart_data', [])
                            if chart_data_points:
                                self.draw_mini_chart(chart_data_points, coin_symbol, buy_price_value, buy_time_stamp)
                            else:
                                self.canvas_chart.delete("all")
                                self.lbl_chart_title.config(text="Mini-Gráfico (Inativo)", fg="#9aa0a6")

                            aptas_list = state_data.get('hot_cache', [])
                            geladeira_list = state_data.get('cold_cache', [])
                            
                            if getattr(self, 'last_aptas', None) != aptas_list:
                                self.list_hot.delete(0, tk.END)
                                for item in aptas_list: self.list_hot.insert(tk.END, item)
                                self.last_aptas = aptas_list
                                
                            if getattr(self, 'last_geladeira', None) != geladeira_list:
                                self.list_cold.delete(0, tk.END)
                                for item in geladeira_list: self.list_cold.insert(tk.END, item)
                                self.last_geladeira = geladeira_list
                            
            except Exception: pass 
                
        self.root.after(1000, self.check_bot_state_json)

    def read_output(self):
        process_ref = self.process 
        if not process_ref: return
        
        try:
            for log_line in iter(process_ref.stdout.readline, ''):
                if " - " in log_line:
                    parts = log_line.split(" - ", 1)
                    time_part = parts[0]
                    if "," in time_part:
                        time_part = time_part.split(",")[0]
                    log_line = f"{time_part} - {parts[1]}"
                self.log_message(log_line)
        except Exception:
            pass
        
        try:
            process_ref.stdout.close()
            process_ref.wait()
        except Exception:
            pass
        
        if self.bot_running:
            self.root.after(0, lambda: self.lbl_det_atu.config(text="Status: Erro de execução de processo. Verifique log console.", fg=self.accent_red))
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
                    self.current_balance = total_atual_value
                    if self.initial_balance == 0.0:
                        self.initial_balance = total_atual_value
                        self._save_gui_state()
                        
                    cor_ping = self.accent_green if ping_latency_ms <= 600 else (self.accent_yellow if ping_latency_ms <= 1000 else self.accent_red)
                    self.root.after(0, lambda u=self.initial_balance, p=ping_latency_ms, c=cor_ping: [
                        self.lbl_inicial.config(text=f"[S] Saldo Inicial: ${u:.2f}"),
                        self.lbl_ping.config(text=f"PING: {p} ms", fg=c)
                    ])
                    break
                time.sleep(1)
            
            while self.bot_running:
                start_time = time.time()
                total_atual_value = self.get_total_usdt_balance(binance_client_instance, bridge_symbol)
                ping_latency_ms = int((time.time() - start_time) * 1000)
                
                if total_atual_value > 0:
                    self.current_balance = total_atual_value
                    
                if self.initial_balance > 0 and total_atual_value > 0:
                    profit_loss_value = total_atual_value - self.initial_balance
                    profit_loss_percentage = (profit_loss_value / self.initial_balance) * 100
                    cor_texto_pl = self.accent_green if profit_loss_value >= 0 else self.accent_red
                else:
                    profit_loss_value = profit_loss_percentage = 0
                    cor_texto_pl = self.fg_text

                if total_atual_value > 0:
                    cor_ping = self.accent_green if ping_latency_ms <= 600 else (self.accent_yellow if ping_latency_ms <= 1000 else self.accent_red)
                    self.root.after(0, lambda a=total_atual_value, p=profit_loss_value, pp=profit_loss_percentage, c=cor_texto_pl, pi=ping_latency_ms, cp=cor_ping: [
                        self.lbl_atual.config(text=f"[$] Saldo Atual: ${a:.2f}"),
                        self.lbl_pl.config(text=f"P/L Total: ${p:.2f} ({pp:.2f}%)", fg=c),
                        self.lbl_ping.config(text=f"PING: {pi} ms", fg=cp)
                    ])
                time.sleep(15)
        except: pass

    def start_bot(self):
        if self.bot_running or self.process is not None:
            self.log_message("[INFO] A instância da engine já encontra-se ativa.\n")
            return
            
        self.log_message("[INFO] Inicializando ambiente em modo seguro...\n")
        self.lbl_det_atu.config(text="Status: Alocando memória da engine...", fg=self.fg_text)
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
        if self.process: 
            try:
                self.process.kill() 
            except Exception: pass
            self.process = None
        self.bot_running = False
        self.lbl_det_atu.config(text="Status: Processo suspenso.", fg=self.fg_text)

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