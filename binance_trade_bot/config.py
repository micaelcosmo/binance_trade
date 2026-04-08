import configparser
import os

from .models import Coin

CFG_FL_NAME = "user.cfg"
USER_CFG_SECTION = "binance_user_config"


class Config:
    """
    Classe de configuracao central do sistema.
    Realiza o parse seguro do arquivo user.cfg com fallbacks institucionais,
    evitando falhas criticas por atributos ausentes ou vazios.
    """

    def __init__(self):
        config = configparser.ConfigParser()
        
        config["DEFAULT"] = {
            "bridge": "USDT",
            "use_margin": "no",
            "scout_multiplier": "5",
            "scout_margin": "0.8",
            "scout_sleep_time": "60",
            "hourToKeepScoutHistory": "1",
            "tld": "com",
            "strategy": "profit_gain",
            "sell_timeout": "0",
            "buy_timeout": "0",
            "testnet": "False",
        }

        if not os.path.exists(CFG_FL_NAME):
            print("⚠️ Arquivo de configuracao (user.cfg) nao encontrado! Assumindo valores padrao...")
            config[USER_CFG_SECTION] = {}
        else:
            config.read(CFG_FL_NAME)

        # Funcoes de seguranca para evitar ValueError com strings vazias ("")
        def get_safe_float(key, default_val):
            val = os.environ.get(key.upper()) or config.get(USER_CFG_SECTION, key, fallback=str(default_val))
            try:
                return float(val) if str(val).strip() != "" else float(default_val)
            except Exception:
                return float(default_val)

        def get_safe_int(key, default_val):
            val = os.environ.get(key.upper()) or config.get(USER_CFG_SECTION, key, fallback=str(default_val))
            try:
                return int(val) if str(val).strip() != "" else int(default_val)
            except Exception:
                return int(default_val)

        self.BINANCE_API_KEY = os.environ.get("API_KEY") or config.get(USER_CFG_SECTION, "api_key", fallback="")
        self.BINANCE_API_SECRET_KEY = os.environ.get("API_SECRET_KEY") or config.get(USER_CFG_SECTION, "api_secret_key", fallback="")
        self.BINANCE_TLD = os.environ.get("TLD") or config.get(USER_CFG_SECTION, "tld", fallback="com")

        self.BRIDGE_SYMBOL = os.environ.get("BRIDGE_SYMBOL") or config.get(USER_CFG_SECTION, "bridge", fallback="USDT")
        self.BRIDGE = Coin(self.BRIDGE_SYMBOL, False)
        
        self.TESTNET = os.environ.get("TESTNET") or config.getboolean(USER_CFG_SECTION, "testnet", fallback=False)

        self.CURRENT_COIN_SYMBOL = os.environ.get("CURRENT_COIN_SYMBOL") or config.get(USER_CFG_SECTION, "current_coin", fallback="")
        self.STRATEGY = os.environ.get("STRATEGY") or config.get(USER_CFG_SECTION, "strategy", fallback="profit_gain")

        # Configuracoes Avancadas IA (Extraidas com seguranca anti-crash)
        self.daily_profit_target_pct = get_safe_float("daily_profit_target_pct", 5.0)
        self.max_daily_trades = get_safe_int("max_daily_trades", 3)
        self.base_stop_loss_pct = get_safe_float("base_stop_loss_pct", 7.0)
        self.disaster_stop_pct = get_safe_float("disaster_stop_pct", 15.0)
        self.trailing_activation_pct = get_safe_float("trailing_activation_pct", 1.5)
        self.trailing_drop_pct = get_safe_float("trailing_drop_pct", 0.3)
        self.ai_cooldown_minutes = get_safe_float("ai_cooldown_minutes", 45.0)

        self.SCOUT_SLEEP_TIME = get_safe_int("scout_sleep_time", 60)
        self.SELL_TIMEOUT = os.environ.get("SELL_TIMEOUT") or config.get(USER_CFG_SECTION, "sell_timeout", fallback="0")
        self.BUY_TIMEOUT = os.environ.get("BUY_TIMEOUT") or config.get(USER_CFG_SECTION, "buy_timeout", fallback="0")
        self.USE_MARGIN = os.environ.get("USE_MARGIN") or config.get(USER_CFG_SECTION, "use_margin", fallback="yes")
        self.SCOUT_MARGIN = get_safe_float("scout_margin", 1.2)
        self.SCOUT_MULTIPLIER = get_safe_float("scout_multiplier", 5.0)
        self.SCOUT_HISTORY_PRUNE_TIME = get_safe_float("hourToKeepScoutHistory", 1.0)

        supported_coin_list = [coin.strip() for coin in os.environ.get("SUPPORTED_COIN_LIST", "").split() if coin.strip()]
        
        if not supported_coin_list:
            file_to_read = "supported_coin_list.txt" if os.path.exists("supported_coin_list.txt") else ("supported_coin_list" if os.path.exists("supported_coin_list") else None)
            if file_to_read:
                with open(file_to_read) as file_handler:
                    for coin_line in file_handler:
                        coin_line = coin_line.strip()
                        if not coin_line or coin_line.startswith("#") or coin_line in supported_coin_list:
                            continue
                        supported_coin_list.append(coin_line)
                        
        self.SUPPORTED_COIN_LIST = supported_coin_list