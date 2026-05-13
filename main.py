import asyncio
from datetime import datetime
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
    symbol = 'BTC/USDT'
    timeframe = '15m' 
    poll_interval_seconds = 60 
    
    log.info(f"🚀 Запуск Moneymaker2. Пара: {symbol}, ТФ: {timeframe}, Пинг: {poll_interval_seconds}с")
    
    provider = MarketDataProvider(exchange_id='binance')
    engine = VSAStrategyEngine(symbol)
    trader = LivePaperTrader(start_balance=1000.0)
    risk_manager = RiskManager(account_balance_usd=trader.balance, risk_per_trade_percent=1.0)
    notifier = TelegramNotifier()
    
    # Теперь отправляем владельцу (тебе)
    await notifier.send_to_owner(f"🚀 <b>Moneymaker2 запущен!</b>\nПара: {symbol}\nТаймфрейм: {timeframe}")
    
    try:
        while True:
            log.debug("Получение свежих данных с биржи...")
            
            df = await provider.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
            current_candle = df.iloc[-1]
            
            closed_trades = trader.update_prices(
                symbol=symbol, 
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
                
                # Отчеты о закрытых сделках отправляем и тебе, и трейдеру
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
                    
                    # Генерируем уникальный ID сигнала на основе времени
                    sig_id = str(int(signal.timestamp.timestamp()))
                    
                    log.info(f"✅ СИГНАЛ НАЙДЕН: {instruction.action} {symbol}. Ожидание валидации трейдером...")
                    
                    tg_msg = (f"🔥 <b>СИГНАЛ: {instruction.action} {symbol}</b>\n\n"
                            f"<b>Логика:</b> {signal.reason}\n\n"
                            f"<b>План сделки (Риск ${instruction.risk_usd:.2f}):</b>\n"
                            f"Вход: {instruction.entry_price:.2f}\n"
                            f"Stop-Loss: {instruction.stop_loss:.2f}\n"
                            f"Take-Profit: {instruction.take_profit:.2f}\n"
                            f"Размер: {instruction.position_size_coins:.5f} монеты")
                    
                    # Отправляем сообщение Трейдеру С КНОПКОЙ
                    await notifier.send_to_trader_with_keyboard(tg_msg, signal_id=sig_id)
                    
                    # Отправляем сообщение Тебе (как инфо)
                    await notifier.send_to_owner(f"ℹ️ Сигнал {instruction.action} отправлен трейдеру на проверку.")
                    
                    # ПОКА ЧТО: Мы просто отправляем сигнал, но в сделку не входим. 
                    # Входим только в ручном/бумажном режиме или после настройки TelegramListener'а (следующий шаг).
                    
                else:
                    log.debug("Сигналов нет. Ожидание.")

            await asyncio.sleep(poll_interval_seconds)

    except KeyboardInterrupt:
        log.info("🛑 Работа бота остановлена пользователем.")
        await notifier.send_to_owner("🛑 Работа бота остановлена.")
    finally:
        await provider.close()

async def main():
    """Точка входа, запускающая бота и слушателя кнопок параллельно."""
    bot_task = asyncio.create_task(run_live_bot())
    listener = TelegramListener()
    listener_task = asyncio.create_task(listener.listen())
    
    await asyncio.gather(bot_task, listener_task)

if __name__ == "__main__":
    asyncio.run(main())
