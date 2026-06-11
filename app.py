import codecs
import json
import os
import subprocess
import sys
import threading
import time

from flask import Flask, render_template, request
from flask_socketio import SocketIO
from binance.client import Client
from binance_trade_bot.config import Config


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'binance_bot_pro_dev_key_secure'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

bot_process = None
bot_running = False
saldo_inicial = 0.0
saldo_atual = 0.0
locked_at_trade_count = -1

current_motor_cooldown = 15
current_bb_std = 2.0

GUI_STATE_FILE = os.path.join(BASE_DIR, "gui_state.json")


def _load_gui_state():
    global saldo_inicial
    if os.path.exists(GUI_STATE_FILE):
        try:
            with open(GUI_STATE_FILE, "r", encoding="utf-8") as f:
                state_data = json.load(f)
                saldo_inicial = state_data.get("saldo_inicial", 0.0)
        except Exception:
            pass


def _save_gui_state():
    global saldo_inicial
    try:
        with open(GUI_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"saldo_inicial": saldo_inicial}, f)
    except Exception:
        pass


def get_total_usdt_balance(client, bridge_symbol):
    try:
        acc = client.get_account()
        tickers = {t['symbol']: float(t['price']) for t in client.get_symbol_ticker()}
        total_usdt = 0.0
        
        for b in acc['balances']:
            free = float(b['free']) + float(b['locked'])
            if free > 0:
                asset = b['asset']
                if asset == bridge_symbol:
                    total_usdt += free
                else:
                    sym = f"{asset}{bridge_symbol}"
                    if sym in tickers:
                        total_usdt += free * tickers[sym]
        return total_usdt
    except Exception:
        return 0.0


def update_stats_loop():
    global saldo_inicial, saldo_atual, bot_running
    
    try:
        config_instance = Config()
        client = Client(
            config_instance.BINANCE_API_KEY, 
            config_instance.BINANCE_API_SECRET_KEY, 
            tld=config_instance.BINANCE_TLD
        )
        bridge = getattr(config_instance, 'BRIDGE', 'USDT')
        if hasattr(bridge, 'symbol'):
            bridge = bridge.symbol
    except Exception as e:
        print(f"Erro ao carregar Client da Binance no Flask: {e}")
        return

    for _ in range(3):
        start_time = time.time()
        total_usdt = get_total_usdt_balance(client, bridge)
        ping_ms = int((time.time() - start_time) * 1000)
        
        if total_usdt > 0:
            saldo_atual = total_usdt
            if saldo_inicial == 0.0:
                saldo_inicial = total_usdt
                _save_gui_state()
            
            socketio.emit('update_balance', {
                'inicial': saldo_inicial, 
                'ping': ping_ms
            })
            break
        time.sleep(1)
        
    while True:
        if bot_running:
            start_time = time.time()
            total_usdt = get_total_usdt_balance(client, bridge)
            ping_ms = int((time.time() - start_time) * 1000)
            
            if total_usdt > 0:
                saldo_atual = total_usdt
                
            if saldo_inicial > 0 and total_usdt > 0:
                pl_value = total_usdt - saldo_inicial
                pl_perc = (pl_value / saldo_inicial) * 100
            else:
                pl_value = pl_perc = 0
                
            socketio.emit('update_balance', {
                'inicial': saldo_inicial,
                'atual': total_usdt,
                'pl': pl_value,
                'pl_perc': pl_perc,
                'ping': ping_ms
            })
        time.sleep(15)


def monitor_bot_status():
    global locked_at_trade_count, current_motor_cooldown, current_bb_std
    
    while True:
        if bot_running:
            status_file = os.path.join(BASE_DIR, "bot_status.json")
            if os.path.exists(status_file):
                try:
                    with open(status_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        
                        if data:
                            is_em_operacao = "Em Operação" in data.get("status", "")
                            
                            cooldown_until = data.get('cooldown_until', 0.0)
                            if not is_em_operacao:
                                if time.time() < cooldown_until:
                                    restante = int(cooldown_until - time.time())
                                    mins, secs = divmod(restante, 60)
                                    data['countdown_str'] = f"⏳ Próxima Análise: {mins:02d}:{secs:02d}"
                                else:
                                    data['countdown_str'] = "⏳ Próxima Análise: Executando..."
                            else:
                                data['countdown_str'] = "⏳ Próxima Análise: -- (Em operação)"
                                
                            trades_no_dia = data.get("daily_trades", data.get("trades_no_dia", 0))
                            if not is_em_operacao and trades_no_dia > locked_at_trade_count:
                                data['unlock_add_trade'] = True
                            else:
                                data['unlock_add_trade'] = False

                            last_hb_ts = data.get("last_heartbeat_ts", 0.0)
                            if last_hb_ts > 0:
                                delta_hb = time.time() - last_hb_ts
                                data['hb_str'] = time.strftime("%H:%M:%S", time.localtime(last_hb_ts))
                                data['hb_color'] = '#10b981' if delta_hb <= 80 else ('#f59e0b' if delta_hb <= 300 else '#ef4444')
                            
                            current_motor_cooldown = data.get('motor_cooldown_minutes', current_motor_cooldown)
                            current_bb_std = data.get('bollinger_std', current_bb_std)
                            data['current_motor_cooldown'] = current_motor_cooldown
                            data['current_bb_std'] = current_bb_std
                                
                            socketio.emit('update_metrics', data)
                except Exception:
                    pass
        time.sleep(1)


def read_process_output():
    global bot_process, bot_running
    
    if bot_process:
        for line in iter(bot_process.stdout.readline, ''):
            texto = line.strip()
            if texto:
                if " - " in texto:
                    parts = texto.split(" - ", 1)
                    time_part = parts[0]
                    if "," in time_part:
                        time_part = time_part.split(",")[0]
                    texto = f"{time_part} - {parts[1]}"
                socketio.emit('new_log', {'message': texto})
                
        bot_process.stdout.close()
        bot_process.wait()
        
        bot_running = False
        socketio.emit('new_log', {'message': '[!] Processo do bot finalizado ou suspenso.'})
        socketio.emit('status_parado')


@app.route('/')
def index():
    try:
        strategy = Config().STRATEGY.lower()
    except Exception:
        strategy = 'default'
        
    try:
        git_version = subprocess.check_output(
            ["git", "describe", "--tags", "--abbrev=0"], 
            stderr=subprocess.DEVNULL, 
            cwd=BASE_DIR
        ).decode('utf-8').strip()
    except Exception:
        git_version = "v3.6.6"
        
    return render_template('index.html', strategy=strategy, versao=git_version)


@socketio.on('connect')
def handle_connect():
    # Envia os saldos imediatamente para quem acabou de abrir a página (F5)
    pl_value = (saldo_atual - saldo_inicial) if (saldo_inicial > 0 and saldo_atual > 0) else 0
    pl_perc = (pl_value / saldo_inicial * 100) if saldo_inicial > 0 else 0
    
    socketio.emit('update_balance', {
        'inicial': saldo_inicial,
        'atual': saldo_atual if saldo_atual > 0 else saldo_inicial,
        'pl': pl_value,
        'pl_perc': pl_perc,
        'ping': 0
    }, to=request.sid)

    # Força o envio do último radar/json lido pelo sistema para a tela do usuário
    status_file = os.path.join(BASE_DIR, "bot_status.json")
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    data['current_motor_cooldown'] = current_motor_cooldown
                    data['current_bb_std'] = current_bb_std
                    socketio.emit('update_metrics', data, to=request.sid)
        except Exception:
            pass


@socketio.on('start_bot')
def handle_start():
    global bot_process, bot_running
    
    if bot_running or bot_process is not None:
        socketio.emit('new_log', {'message': '[INFO] A instancia da engine ja encontra-se ativa.\n'})
        return
        
    socketio.emit('new_log', {'message': '[INFO] Inicializando ambiente em modo seguro (Cloud)...\n'})
    
    status_file = os.path.join(BASE_DIR, "bot_status.json")
    with open(status_file, "w", encoding="utf-8") as f: 
        json.dump({}, f)
    
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = BASE_DIR 
    
    bot_running = True
    bot_process = subprocess.Popen(
        [sys.executable, "-m", "binance_trade_bot"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding='utf-8',
        errors='replace',
        env=env,
        cwd=BASE_DIR 
    )
    
    threading.Thread(target=read_process_output, daemon=True).start()


@socketio.on('stop_bot')
def handle_stop():
    global bot_process, bot_running
    
    if bot_process:
        try:
            bot_process.kill()
        except Exception:
            pass
        bot_process = None
        
    bot_running = False
    socketio.emit('new_log', {'message': '[!] Bot interrompido pelo usuário.'})
    socketio.emit('status_parado')


@socketio.on('reset_initial_balance')
def handle_reset_initial():
    global saldo_inicial, saldo_atual
    
    if saldo_atual > 0:
        saldo_inicial = saldo_atual
        _save_gui_state()
        socketio.emit('update_balance', {'inicial': saldo_inicial})
        socketio.emit('new_log', {'message': '\n[OK] Capital inicial recalibrado com sucesso.\n'})


@socketio.on('reset_scoreboard')
def handle_reset_scoreboard():
    try:
        with open(os.path.join(BASE_DIR, "reset_trades.flag"), "w", encoding="utf-8") as f:
            f.write("reset")
            
        status_file = os.path.join(BASE_DIR, "bot_status.json")
        if os.path.exists(status_file):
            with open(status_file, "r", encoding="utf-8") as f:
                state_data = json.load(f)
            state_data["trades_won"] = 0
            state_data["trades_lost"] = 0
            with open(status_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
                
        pg_file = os.path.join(BASE_DIR, "profit_gain_state.json")
        if os.path.exists(pg_file):
            with open(pg_file, "r", encoding="utf-8") as f:
                pg_state = json.load(f)
            pg_state["trades_won"] = 0
            pg_state["trades_lost"] = 0
            with open(pg_file, "w", encoding="utf-8") as f:
                json.dump(pg_state, f)

        socketio.emit('new_log', {'message': '\n[OK] Placar financeiro e estatisticas reiniciados.\n'})
    except Exception as e:
        socketio.emit('new_log', {'message': f'\n[ERROR] Falha ao zerar placar: {e}\n'})


@socketio.on('add_trade_chance')
def handle_add_trade():
    global locked_at_trade_count
    
    with open(os.path.join(BASE_DIR, "add_trade.flag"), "w", encoding="utf-8") as f:
        f.write("1")
        
    current_trades = 0
    status_file = os.path.join(BASE_DIR, "bot_status.json")
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                current_trades = data.get("daily_trades", 0)
        except Exception:
            pass
            
    locked_at_trade_count = current_trades
    socketio.emit('lock_add_trade')
    socketio.emit('new_log', {'message': '\n[+] Extensao de limite de operacoes solicitada ao motor central.\n'})


@socketio.on('cycle_cooldown')
def handle_cycle_cooldown(data):
    global current_motor_cooldown
    cycle = {15: 30, 30: 45, 45: 15}
    next_cd = cycle.get(int(data.get('current', 15)), 15)
    current_motor_cooldown = next_cd
    
    try:
        with open(os.path.join(BASE_DIR, "cooldown.flag"), "w", encoding="utf-8") as f:
            f.write(str(next_cd))
        socketio.emit('new_log', {'message': f'\n[+] Tempo de verificacao basica ajustado para {next_cd} minutos.\n'})
        socketio.emit('update_button_states', {'cooldown': next_cd})
    except Exception as e:
        socketio.emit('new_log', {'message': f'\n[ERROR] Falha ao ajustar tempo: {e}\n'})


@socketio.on('cycle_bb_std')
def handle_cycle_bb_std(data):
    global current_bb_std
    cycle = {2.0: 1.8, 1.8: 1.5, 1.5: 2.0}
    next_std = cycle.get(float(data.get('current', 2.0)), 2.0)
    current_bb_std = next_std
    
    try:
        with open(os.path.join(BASE_DIR, "bb_std.flag"), "w", encoding="utf-8") as f:
            f.write(str(next_std))
        socketio.emit('new_log', {'message': f'\n[+] Desvio Padrão de Bollinger ajustado para {next_std}.\n'})
        socketio.emit('update_button_states', {'bb_std': next_std})
    except Exception as e:
        socketio.emit('new_log', {'message': f'\n[ERROR] Falha ao ajustar Bollinger: {e}\n'})


@socketio.on('force_sell_action')
def handle_force_sell():
    try:
        with open(os.path.join(BASE_DIR, "force_sell.flag"), "w", encoding="utf-8") as f:
            f.write("trigger_manual_sell")
        socketio.emit('new_log', {'message': '\n[INFO] Diretiva de venda manual interceptada. Aguardando execucao.\n'})
    except Exception as e:
        socketio.emit('new_log', {'message': f'\n[ERROR] Falha na emissao do comando: {e}\n'})


@socketio.on('request_update')
def handle_request_update():
    try:
        with open(os.path.join(BASE_DIR, "update_pending.flag"), "w", encoding="utf-8") as f:
            f.write("pending")
        socketio.emit('new_log', {'message': '\n[INFO] Flag de atualizacao gerada. O bot processara o git pull.\n'})
    except Exception as e:
        socketio.emit('new_log', {'message': f'\n[ERROR] Falha na flag de atualizacao: {e}\n'})


@socketio.on('request_ai_report')
def handle_ai_report():
    report = "Nenhum relatorio foi processado neste ciclo."
    status_file = os.path.join(BASE_DIR, "bot_status.json")
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                report = data.get("full_ai_report", data.get("ai_report", report))
        except Exception:
            pass
    report_html = report.replace('\n', '<br>')
    socketio.emit('show_modal_html', {'title': '🧠 Parecer Analítico Institucional', 'content': report_html})


@socketio.on('request_daily_history')
def handle_daily_history():
    hist = []
    status_file = os.path.join(BASE_DIR, "bot_status.json")
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                hist = data.get("daily_history", [])
        except Exception:
            pass
            
    formatted_html = ""
    if not hist:
        formatted_html = "Nenhuma transacao registrada na data vigente."
    else:
        for item in hist:
            cor = "text-green-500" if "+" in item.get('result', '') or "+" in item.get('resultado', '') else "text-red-500"
            resultado = item.get('result', item.get('resultado', ''))
            motivo = item.get('reason', item.get('motivo', ''))
            formatted_html += f"<div class='mb-4'><span class='text-gray-400'>[{item['time']}]</span> <span class='{cor} font-bold'>{item['coin']: <8} -> {resultado}</span><br><span class='text-gray-500 ml-4'>Motivo: {motivo}</span></div>"
            
    socketio.emit('show_modal_html', {'title': '📜 Extrato de Operações Diárias', 'content': formatted_html})


@socketio.on('request_dossier')
def handle_dossier():
    dossier = []
    status_file = os.path.join(BASE_DIR, "bot_status.json")
    if os.path.exists(status_file):
        try:
            with open(status_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                dossier = data.get("last_dossier", [])
        except Exception:
            pass
            
    html_out = ""
    if not dossier:
        html_out = "<span class='text-gray-400'>Nenhum dossiê foi retido na memória. O mercado não apresentou quedas agudas suficientes no último ciclo.</span><br>"
    else:
        for item in dossier:
            coin = item.get("coin", "N/A")
            html_out += f"<div class='border border-gray-800 p-3 rounded mb-4 bg-[#0a0c10]'>"
            html_out += f"<div class='text-blue-400 font-bold mb-2 pb-2 border-b border-gray-800'>🪙 MOEDA: {coin}</div>"
            
            html_out += f"<div class='text-gray-300'>💵 Preço Atual: ${item.get('current_price', 0):.6f}</div>"
            html_out += f"<div class='text-gray-300 mb-2'>📉 Variação 24h: {item.get('change_24h_pct', '0%')}</div>"
            
            min_24h = float(str(item.get('min_24h_change_pct', '0')).replace('%', '').replace('+', ''))
            req_atr = float(str(item.get('required_atr_bottom_pct', '0')).replace('%', '').replace('+', ''))
            cor_atr = "text-green-500" if min_24h <= req_atr else "text-orange-400"
            html_out += f"<div class='{cor_atr} font-semibold'>🕳️ Fundo 24h: {item.get('min_24h_change_pct', '0%')} | Exigido: {item.get('required_atr_bottom_pct', '0%')}</div>"
            
            b_15_bool = item.get("touched_lower_band_15m")
            cor_b15 = "text-green-500" if b_15_bool else "text-orange-400"
            html_out += f"<div class='{cor_b15} font-semibold'>🎯 Tocou Bollinger Inferior (15m): {'SIM' if b_15_bool else 'NÃO'} | Mínima: ${item.get('lowest_15m_val', 0):.6f} | Banda: ${item.get('bbl_15m_target', 0):.6f}</div>"
            
            b_1h_bool = item.get("touched_lower_band_1h")
            cor_b1h = "text-green-500" if b_1h_bool else "text-orange-400"
            html_out += f"<div class='{cor_b1h} font-semibold'>🎯 Tocou Bollinger Inferior (1H): {'SIM' if b_1h_bool else 'NÃO'} | Mínima: ${item.get('lowest_1h_val', 0):.6f} | Banda: ${item.get('bbl_1h_target', 0):.6f}</div>"
            
            macd_1h_bool = item.get("macd_1h_shifting_up")
            html_out += f"<div class='{'text-green-500' if macd_1h_bool else 'text-orange-400'} font-semibold'>📈 MACD 1H Perdendo Força Vendedora: {'SIM' if macd_1h_bool else 'NÃO'}</div>"
            
            macd_15m_bool = item.get("macd_histogram_15m_positive")
            html_out += f"<div class='{'text-green-500' if macd_15m_bool else 'text-orange-400'} font-semibold'>🚀 MACD 15m Positivo (Momentum): {'SIM' if macd_15m_bool else 'NÃO'}</div>"
            
            vol_bool = item.get("volume_15m_above_avg")
            vol_pct = item.get("volume_15m_pct", 0.0)
            html_out += f"<div class='{'text-green-500' if vol_bool else 'text-orange-400'} font-semibold'>📊 Volume 15m (>= 80% Média): {'SIM' if vol_bool else 'NÃO'} | Atual: {vol_pct:.2f}%</div>"
            
            ema_str = item.get('ema21_1h_distance_pct', '0%')
            ema_val = float(str(ema_str).replace('%', '').replace('+', ''))
            html_out += f"<div class='{'text-green-500' if ema_val < -1.00 else 'text-orange-400'} font-semibold'>📏 Distância EMA21 (1H): {ema_str} | Esperado: < -1.00%</div>"
            
            html_out += f"</div>"

    socketio.emit('show_modal_html', {'title': '📊 Dossiê do Motor Quantitativo', 'content': html_out})


if __name__ == '__main__':
    if sys.platform == 'win32':
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        
    _load_gui_state()
    socketio.start_background_task(monitor_bot_status)
    socketio.start_background_task(update_stats_loop)
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)