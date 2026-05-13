import asyncio
from datetime import datetime
from config.settings import TRADING_SYMBOL, TIMEFRAME, POLL_INTERVAL_SECONDS, START_BALANCE_USD, RISK_PER_TRADE_PERCENT
from core_lib.data_provider import MarketDataProvider
from strategy_engine.vsa_strategy import VSAStrategyEngine
from risk_management.manager import RiskManager
from execution.live_paper import LivePaperTrader
from execution.telegram_notifier import TelegramNotifier
from execution.telegram_listener import TelegramListener
from core_lib.logger import setup_logger

# Главный логгер для Event Loop
log = setup_logger("MainLoop")

async def run_live_bot():
    log.info(f"🚀 Запуск Moneymaker2. Пара: {TRADING_SYMBOL}, ТФ: {TIMEFRAME}, Пинг: {POLL_INTERVAL_SECONDS}с")
    
    provider = MarketDataProvider(exchange_id='binance')
    engine = VSAStrategyEngine(TRADING_SYMBOL)
    trader = LivePaperTrader(start_balance=START_BALANCE_USD)
    risk_manager = RiskManager(account_balance_usd=trader.balance, risk_per_trade_percent=RISK_PER_TRADE_PERCENT)
    notifier = TelegramNotifier()
    
    await notifier.send_to_owner(f"🚀 <b>Moneymaker2 запущен!</b>\nПара: {TRADING_SYMBOL}\nТаймфрейм: {TIMEFRAME}")
    
    try:
        while True:
            log.debug("Получение свежих данных с биржи...")
            
            df = await provider.fetch_ohlcv(TRADING_SYMBOL, timeframe=TIMEFRAME, limit=100)
            current_candle = df.iloc[-1]
            
            closed_trades = trader.update_prices(
                symbol=TRADING_SYMBOL, 
                current_price=current_candle['close'],
                high=current_candle['high'],
                low=current_candle['low']
            )
            
            for t in closed_trades:
                emoji = "✅" if t['pnl_usd'] > 0 else "❌"
                msg_txt = (f"СДЕЛКА ЗАКРЫТА: {t['action']} | Причина: {t['reason']} | "
                           f"Вход: {t['entry_price']:.2f} -> Выход: {t['exit_price']:.2f} | PNL: ${t['pnl_usd']:.2f}")
                log.info(f"🔔 {msg_txt}")
                
                tg_msg = (f"{emoji} <b>СДЕЛКА ЗАКРЫТА: {t['action']}</b>\n\n"
                       f"<b>Причина выхода:</b> {t['reason']}\n"
                       f"<b>Вход:</b> {t['entry_price']:.2f}\n"
                       f"<b>Выход:</b> {t['exit_price']:.2f}\n"
                       f"<b>PNL:</b> ${t['pnl_usd']:.2f}\n"
                       f"<b>Новый баланс:</b> ${trader.balance:.2f}")
                
                await notifier.send_to_owner(tg_msg)
                await notifier.send_to_trader_with_keyboard(tg_msg, signal_id=f"closed_{int(datetime.now().timestamp())}")

            if trader.active_positions:
                pos = trader.active_positions[0]
                log.debug(f"В сделке: {pos.action} от {pos.entry_price:.2f}. Текущий PNL: ${pos.current_pnl_usd:.2f}")
            else:
                signal = engine.analyze(df)
                
                if signal:
                    risk_manager.account_balance_usd = trader.balance
                    instruction = risk_manager.validate_and_size(signal)
                    
                    sig_id = str(int(signal.timestamp.timestamp()))
                    log.info(f"✅ СИГНАЛ НАЙДЕН: {instruction.action} {TRADING_SYMBOL}. Ожидание валидации трейдером...")
                    
                    tg_msg = (f"🔥 <b>СИГНАЛ: {instruction.action} {TRADING_SYMBOL}</b>\n\n"
                            f"<b>Логика:</b> {signal.reason}\n\n"
                            f"<b>План сделки (Риск ${instruction.risk_usd:.2f}):</b>\n"
                            f"Вход: {instruction.entry_price:.2f}\n"
                            f"Stop-Loss: {instruction.stop_loss:.2f}\n"
                            f"Take-Profit: {instruction.take_profit:.2f}\n"
                            f"Размер: {instruction.position_size_coins:.5f} монеты")
                    
                    await notifier.send_to_trader_with_keyboard(tg_msg, signal_id=sig_id)
                    await notifier.send_to_owner(f"ℹ️ Сигнал {instruction.action} отправлен трейдеру на проверку.")
                else:
                    log.debug("Сигналов нет. Ожидание.")

            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        log.info("🛑 Работа бота остановлена пользователем.")
        await notifier.send_to_owner("🛑 Работа бота остановлена.")
    finally:
        await provider.close()

async def main():
    bot_task = asyncio.create_task(run_live_bot())
    listener = TelegramListener()
    listener_task = asyncio.create_task(listener.listen())
    await asyncio.gather(bot_task, listener_task)

if __name__ == "__main__":
    asyncio.run(main())
