import pandas as pd
import aiohttp
from core_lib.logger import setup_logger
from config.settings import MT5_SERVER_URL, TIMEFRAME, MT5_MAX_CONCURRENT_REQUESTS # Import MT5_SERVER_URL and TIMEFRAME
import asyncio

class MT5DataProvider:
    """
    Провайдер данных для получения OHLCV с MT5 сервера.
    """
    def __init__(self):
        self.log = setup_logger("MT5DataProvider")
        self.base_url = MT5_SERVER_URL
        self.session = None # aiohttp session will be created on first use
        self._semaphore = asyncio.Semaphore(max(1, int(MT5_MAX_CONCURRENT_REQUESTS)))
        self._timeframe_map = {
            "1m": "M1",
            "5m": "M5",
            "15m": "M15",
            "30m": "M30",
            "1h": "H1",
            "4h": "H4",
            "1d": "D1",
        }

    async def _get_session(self):
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=20)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def fetch_ohlcv(self, symbol: str, timeframe: str = TIMEFRAME, limit: int = 100) -> pd.DataFrame:
        """
        Получает OHLCV данные с MT5 сервера.
        """
        session = await self._get_session()
        
        endpoint = f"{self.base_url}/candles"
        tf = self._timeframe_map.get(timeframe, "H1")
        if timeframe not in self._timeframe_map:
            self.log.warning(f"[{symbol}] Unsupported timeframe '{timeframe}', fallback to H1.")
        params = {
            "symbol": symbol.replace('/', ''), # MT5 symbols usually don't have '/'
            "count": limit,
            "timeframe": tf,
        }
        
        try:
            async with self._semaphore:
                async with session.get(endpoint, params=params) as response:
                    response.raise_for_status() # Raise an exception for HTTP errors
                    data = await response.json()

                if data and "data" in data and data["data"]:
                    df = pd.DataFrame(data["data"])
                    required_price_columns = ["open", "high", "low", "close"]
                    missing = [col for col in required_price_columns if col not in df.columns]
                    if missing:
                        self.log.error(f"[{symbol}] Missing price columns from MT5 response: {missing}")
                        return pd.DataFrame()

                    volume_column = None
                    for candidate in ("tick_volume", "real_volume", "volume"):
                        if candidate in df.columns:
                            volume_column = candidate
                            break
                    if volume_column is None:
                        self.log.warning(f"[{symbol}] Volume column is absent in MT5 response. Using 0.")
                        df["volume"] = 0.0
                    else:
                        df["volume"] = pd.to_numeric(df[volume_column], errors="coerce").fillna(0.0)

                    df['time'] = pd.to_datetime(df['time'], unit='s')
                    df = df.set_index('time')
                    for col in ["open", "high", "low", "close"]:
                        df[col] = pd.to_numeric(df[col], errors="coerce")
                    df = df[['open', 'high', 'low', 'close', 'volume']].dropna()
                    df = df.sort_index()

                    if df.empty:
                        self.log.warning(f"[{symbol}] MT5 response parsed into empty frame.")
                        return pd.DataFrame()

                    self.log.debug(f"[{symbol}] Fetched {len(df)} OHLCV bars from MT5 server.")
                    return df
                else:
                    self.log.warning(f"[{symbol}] No data received from MT5 server for {symbol}.")
                    return pd.DataFrame()
        except aiohttp.ClientError as e:
            self.log.error(f"[{symbol}] Error fetching OHLCV from MT5 server: {e}")
            return pd.DataFrame()
        except asyncio.TimeoutError:
            self.log.error(f"[{symbol}] MT5 server request timeout.")
            return pd.DataFrame()
        except Exception as e:
            self.log.error(f"[{symbol}] An unexpected error occurred: {e}", exc_info=True)
            return pd.DataFrame()

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
            self.log.info("MT5DataProvider aiohttp session closed.")


class MarketDataProvider:
    """
    Провайдер данных, использующий MT5 сервер.
    """
    def __init__(self):
        self.log = setup_logger("MarketDataProvider")
        self.log.info("Инициализация MarketDataProvider для MT5...")
        
        self.mt5_provider = MT5DataProvider()

    async def fetch_ohlcv(self, symbol: str, timeframe: str = TIMEFRAME, limit: int = 100) -> pd.DataFrame:
        # Все запросы теперь идут через MT5DataProvider
        return await self.mt5_provider.fetch_ohlcv(symbol, timeframe, limit)

    async def close(self):
        self.log.info("Закрытие соединений роутера...")
        await self.mt5_provider.close()
