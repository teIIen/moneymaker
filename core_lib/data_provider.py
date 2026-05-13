import ccxt.async_support as ccxt
import pandas as pd
from typing import Optional
from core_lib.logger import setup_logger

class MarketDataProvider:
    """
    Асинхронный провайдер рыночных данных через ccxt.
    Отвечает за получение OHLCV свечей и преобразование их в pandas.DataFrame.
    """
    def __init__(self, exchange_id: str = 'binance'):
        self.log = setup_logger("DataProvider")
        self.log.info(f"Инициализация провайдера данных: {exchange_id}")
        
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'enableRateLimit': True,
        })
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> pd.DataFrame:
        try:
            self.log.debug(f"Запрос {limit} свечей для {symbol} ({timeframe})...")
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            return df
        except Exception as e:
            self.log.error(f"Не удалось получить данные для {symbol}: {e}", exc_info=True)
            raise
    
    async def close(self):
        self.log.info("Закрытие соединения с биржей.")
        await self.exchange.close()
