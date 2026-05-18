import asyncio
import time
from datetime import datetime

from config.settings import POLL_INTERVAL_SECONDS, RISK_PER_TRADE_PERCENT, TIMEFRAME, TRADING_PAIRS
from core_lib.data_provider import MarketDataProvider
from core_lib.logger import setup_logger
from execution.telegram_listener import TelegramListener
from execution.telegram_notifier import TelegramNotifier
from risk_management.manager import RiskManager
from strategy_engine.vsa_strategy import VSAStrategyEngine


log = setup_logger("MainLoop")


async def process_pair(
    symbol: str,
    provider: MarketDataProvider,
    engine: VSAStrategyEngine,
    risk_manager: RiskManager,
    notifier: TelegramNotifier,
):
    try:
        df = await provider.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=200)

        if df is None or df.empty:
            log.warning(f"[{symbol}] No market data received.")
            return

        signal = engine.analyze(df)
        if signal is None:
            return

        instruction = risk_manager.validate_and_size(signal)
        signal_id = f"{symbol.replace('/', '')}_{int(datetime.now().timestamp())}"
        log.info(f"Signal found: {instruction.action} {symbol}")

        metrics = signal.metrics or {}
        trend = metrics.get("trend", "unknown")
        support = metrics.get("recent_support")
        resistance = metrics.get("recent_resistance")
        # VSA Metrics
        vol_ratio = metrics.get("vol_ratio", "N/A")
        is_climax = metrics.get("is_climax", False)
        is_overbought = metrics.get("is_overbought", False)
        is_oversold = metrics.get("is_oversold", False)


        telegram_message = (
            f"<b>SIGNAL: {instruction.action} {symbol}</b>\n\n"
            f"<b>Reason:</b> {signal.reason}\n"
            f"<b>Trend:</b> {trend}\n"
            f"<b>Support:</b> {support}\n"
            f"<b>Resistance:</b> {resistance}\n"
            f"<b>VSA:</b> Vol Ratio={vol_ratio}, Climax={is_climax}, Overbought={is_overbought}, Oversold={is_oversold}\n\n" # Add VSA metrics
            f"<b>Trade plan (risk ${instruction.risk_usd:.2f}):</b>\n"
            f"Entry: {instruction.entry_price:.2f}\n"
            f"Stop-Loss: {instruction.stop_loss:.2f}\n"
            f"Take-Profit: {instruction.take_profit:.2f}\n"
            f"Size: {instruction.position_size_coins:.5f}"
        )

        await notifier.send_to_trader_with_keyboard(telegram_message, signal_id=signal_id)
        owner_message = (
            f"<b>Copy for owner</b>\n"
            f"{telegram_message}\n\n"
            f"<i>Signal ID:</i> {signal_id}"
        )
        await notifier.send_to_owner(owner_message)

    except Exception as exc:
        log.error(f"[{symbol}] Analysis error: {exc}", exc_info=True)


async def run_bot():
    if not TRADING_PAIRS:
        log.warning("TRADING_PAIRS is empty. Nothing to scan.")
        return

    log.info(
        f"Starting Moneymaker2 scanner. Pairs: {len(TRADING_PAIRS)}, "
        f"timeframe: {TIMEFRAME}, interval: {POLL_INTERVAL_SECONDS}s"
    )

    provider = MarketDataProvider()
    engines = {symbol: VSAStrategyEngine(symbol) for symbol in TRADING_PAIRS}
    risk_manager = RiskManager(account_balance_usd=1000, risk_per_trade_percent=RISK_PER_TRADE_PERCENT)
    notifier = TelegramNotifier()

    await notifier.send_to_owner(
        "<b>Moneymaker2 scanner started.</b>\n"
        f"Pairs: {', '.join(TRADING_PAIRS)}\n"
        f"Timeframe: {TIMEFRAME}\n"
        f"Interval: {POLL_INTERVAL_SECONDS}s"
    )

    try:
        while True:
            cycle_started_at = time.monotonic()
            log.info(f"Scanning market: {len(TRADING_PAIRS)} pairs.")

            tasks = [
                process_pair(symbol, provider, engines[symbol], risk_manager, notifier)
                for symbol in TRADING_PAIRS
            ]
            await asyncio.gather(*tasks)

            elapsed_seconds = time.monotonic() - cycle_started_at
            sleep_seconds = max(0.0, POLL_INTERVAL_SECONDS - elapsed_seconds)
            log.info(
                f"Scan completed in {elapsed_seconds:.1f}s. "
                f"Next scan in {sleep_seconds:.1f}s."
            )
            await asyncio.sleep(sleep_seconds)

    except KeyboardInterrupt:
        log.info("Bot stopped by user.")
        await notifier.send_to_owner("Moneymaker2 scanner stopped.")
    finally:
        await provider.close()


async def main():
    bot_task = asyncio.create_task(run_bot())
    listener_task = asyncio.create_task(TelegramListener().listen())
    await asyncio.gather(bot_task, listener_task)


if __name__ == "__main__":
    asyncio.run(main())
