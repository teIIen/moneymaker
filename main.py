import asyncio
from core_lib.data_provider import MarketDataProvider
from strategy_engine.vsa_strategy import VSAStrategyEngine

async def test_strategy():
    provider = MarketDataProvider(exchange_id='binance')
    symbol = 'BTC/USDT'
    engine = VSAStrategyEngine(symbol)

    try:
        # Для анализа уровней нам нужна хорошая история, берем 500 свечей
        print(f"Загружаем 500 свечей по {symbol} для поиска уровней и сигналов...")
        df = await provider.fetch_ohlcv(symbol, timeframe='1h', limit=500)

        # Получаем исторические сигналы по обновленной логике
        historical_signals = engine.backtest(df)
        
        print(f"Найдено сильных сигналов (Climax + Уровень ликвидности): {len(historical_signals)}")
        
        if historical_signals:
            print("\nПоследние 5 сильных сигналов на истории:")
            for sig in historical_signals[-5:]:
                print(f"[{sig.timestamp}] {sig.action} по {sig.price:.2f} ({sig.reason})")

        current_signal = engine.analyze(df)
        print("\nТекущий сигнал (по последней свече):")
        if current_signal:
            print(f"🔥 {current_signal}")
        else:
            print("Пас. Явных сигналов на текущий момент нет (HOLD).")

    finally:
        await provider.close()

if __name__ == "__main__":
    asyncio.run(test_strategy())
