#!python3
import time
import asyncio
import sys
import codecs

# Força o Windows a usar o SelectorEventLoop e UTF-8
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

from .config import Config
from .database import Database
from .logger import Logger
from .scheduler import SafeScheduler
from .strategies import get_strategy

def main():
    logger = Logger()
    logger.info("=============================================")
    logger.info("☕ Aguarde... Inicializando os componentes do Bot")
    logger.info("=============================================")

    config = Config()

    # =====================================================================
    # 🛑 CIRURGIA V3 (CONDICIONAL) 🛑
    # Mata o WebSocket enganando o próprio motor do bot, mas SÓ para a 
    # profit_gain. Se voltar para a default, o WebSocket volta à vida.
    # =====================================================================
    if config.STRATEGY.lower() == 'profit_gain':
        from . import binance_api_manager
        class FakeStreamManager:
            def __init__(self, *args, **kwargs): pass
            def close(self): pass
        # Injeta a classe falsa diretamente no import do motor principal!
        binance_api_manager.BinanceStreamManager = FakeStreamManager

    # Importa o manager APÓS o patch ter sido aplicado (se for o caso)
    from .binance_api_manager import BinanceAPIManager
    
    logger.info("🔗 Estabelecendo conexão segura com a Binance API...")
    
    db = Database(logger, config)
    
    manager = BinanceAPIManager(config, db, logger, config.TESTNET)
    
    try:
        _ = manager.get_account()
    except Exception as e:
        logger.error("🛑 Erro crítico de conexão API. Verifique suas chaves.")
        logger.error(e)
        return
        
    strategy = get_strategy(config.STRATEGY)
    if strategy is None:
        logger.error("Invalid strategy name")
        return
        
    logger.info(f"✅ Estratégia selecionada: {config.STRATEGY}")
    trader = strategy(manager, db, logger, config)
    
    logger.info("Database checked. Bot structure ready.")

    db.create_database()
    db.set_coins(config.SUPPORTED_COIN_LIST)
    db.migrate_old_state()

    trader.initialize()

    logger.info(f"⏳ Bot pronto. A primeira análise ocorrerá em {config.SCOUT_SLEEP_TIME} segundos.")

    schedule = SafeScheduler(logger)
    schedule.every(config.SCOUT_SLEEP_TIME).seconds.do(trader.scout).tag("scouting")
    schedule.every(1).minutes.do(trader.update_values).tag("updating value history")
    schedule.every(1).minutes.do(db.prune_scout_history).tag("pruning scout history")
    schedule.every(1).hours.do(db.prune_value_history).tag("pruning value history")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    finally:
        try:
            manager.stream_manager.close()
        except:
            pass