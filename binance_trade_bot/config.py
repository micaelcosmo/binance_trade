import configparser
import os

from .models import Coin

CFG_FL_NAME = "user.cfg"
USER_CFG_SECTION = "binance_user_config"


class Config:
    """
    Classe de configuracao central do sistema.
    Realiza o parse seguro do arquivo user.cfg com fallbacks institucionais,
    evitando falhas críticas por atributos ausentes.
    """

    def __init__(self):
        # Inicializa o parser nativo de configuracao
        config = configparser.ConfigParser()
        
        # Valores padrao de seguranca para engine fallback
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

        # Chaves de API (Criticas)
        self.BINANCE_API_KEY = os.environ.get("API_KEY") or config.get(USER_CFG_SECTION, "api_key", fallback="")
        self.BINANCE_API_SECRET_KEY = os.environ.get("API_SECRET_KEY") or config.get(USER_CFG_SECTION, "api_secret_key", fallback="")
        self.BINANCE_TLD = os.environ.get("TLD") or config.get(USER_CFG_SECTION, "tld", fallback="com")

        # Dados estruturais de trade
        self.BRIDGE_SYMBOL = os.environ.get("BRIDGE_SYMBOL") or config.get(USER_CFG_SECTION, "bridge", fallback="USDT")
        self.BRIDGE = Coin(self.BRIDGE_SYMBOL, False)
        
        # Testnet (Booleano de seguranca)
        self.TESTNET = os.environ.get("TESTNET") or config.getboolean(USER_CFG_SECTION, "testnet", fallback=False)

        # Parametros core vazios ou padroes
        self.CURRENT_COIN_SYMBOL = os.environ.get("CURRENT_COIN_SYMBOL") or config.get(USER_CFG_SECTION, "current_coin", fallback="")
        self.STRATEGY = os.environ.get("STRATEGY") or config.get(USER_CFG_SECTION, "strategy", fallback="profit_gain")

        # Configuracoes Avancadas IA (Profit Gain Strategy)
        self.daily_profit_target_pct = float(os.environ.get("DAILY_PROFIT_TARGET_PCT") or config.get(USER_CFG_SECTION, "daily_profit_target_pct", fallback="5.0"))
        self.max_daily_trades = int(os.environ.get("MAX_DAILY_TRADES") or config.get(USER_CFG_SECTION, "max_daily_trades", fallback="3"))
        self.base_stop_loss_pct = float(os.environ.get("BASE_STOP_LOSS_PCT") or config.get(USER_CFG_SECTION, "base_stop_loss_pct", fallback="7.0"))
        self.disaster_stop_pct = float(os.environ.get("DISASTER_STOP_PCT") or config.get(USER_CFG_SECTION, "disaster_stop_pct", fallback="15.0"))
        self.trailing_activation_pct = float(os.environ.get("TRAILING_ACTIVATION_PCT") or config.get(USER_CFG_SECTION, "trailing_activation_pct", fallback="1.5"))
        self.trailing_drop_pct = float(os.environ.get("TRAILING_DROP_PCT") or config.get(USER_CFG_SECTION, "trailing_drop_pct", fallback="0.3"))
        self.ai_cooldown_minutes = float(os.environ.get("AI_COOLDOWN_MINUTES") or config.get(USER_CFG_SECTION, "ai_cooldown_minutes", fallback="45.0"))

        # Timeouts e configuracoes do algoritmo legado (Jump/Scout padrao)
        self.SCOUT_SLEEP_TIME = int(os.environ.get("SCOUT_SLEEP_TIME") or config.get(USER_CFG_SECTION, "scout_sleep_time", fallback="60"))
        self.SELL_TIMEOUT = os.environ.get("SELL_TIMEOUT") or config.get(USER_CFG_SECTION, "sell_timeout", fallback="0")
        self.BUY_TIMEOUT = os.environ.get("BUY_TIMEOUT") or config.get(USER_CFG_SECTION, "buy_timeout", fallback="0")
        self.USE_MARGIN = os.environ.get("USE_MARGIN") or config.get(USER_CFG_SECTION, "use_margin", fallback="yes")
        self.SCOUT_MARGIN = float(os.environ.get("SCOUT_MARGIN") or config.get(USER_CFG_SECTION, "scout_margin", fallback="1.2"))
        self.SCOUT_MULTIPLIER = float(os.environ.get("SCOUT_MULTIPLIER") or config.get(USER_CFG_SECTION, "scout_multiplier", fallback="5.0"))
        self.SCOUT_HISTORY_PRUNE_TIME = float(os.environ.get("HOURS_TO_KEEP_SCOUTING_HISTORY") or config.get(USER_CFG_SECTION, "hourToKeepScoutHistory", fallback="1.0"))

        # Extracao estruturada da lista de ativos
        supported_coin_list = [coin.strip() for coin in os.environ.get("SUPPORTED_COIN_LIST", "").split() if coin.strip()]
        
        # Validacao de multiplos arquivos de tracking de ativos
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