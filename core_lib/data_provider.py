import ccxt.async_support as ccxt
import pandas as pd
from typing import Optional

class MarketDataProvider:
    """
    Асинхронный провайдер рыночных данных через ccxt.
    Отвечает за получение OHLCV свечей и преобразование их в pandas.DataFrame.
    """
    def __init__(self, exchange_id: str = 'binance'):
        # Инициализируем биржу по ее ID (binance, bybit, etc.)
        exchange_class = getattr(ccxt, exchange_id)
        self.exchange = exchange_class({
            'enableRateLimit': True,
        })
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1h', limit: int = 100) -> pd.DataFrame:
        """
        Скачивает исторические данные (свечи) и возвращает DataFrame.
        """
        try:
            # Получаем сырые данные
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # Конвертируем в DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Преобразуем timestamp в читаемый datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Приводим типы к float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            return df
        except Exception as e:
            # В будущем здесь будет использоваться логгер проекта
            print(f"[Error] Не удалось получить данные для {symbol}: {e}")
            raise
    
    async def close(self):
        """
        Закрывает соединение с биржей. Обязательно вызывать при завершении работы.
        """
        await self.exchange.close()
