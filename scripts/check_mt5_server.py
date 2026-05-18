import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import TIMEFRAME, TRADING_PAIRS
from core_lib.data_provider import MarketDataProvider


async def check_pair(provider: MarketDataProvider, symbol: str, timeframe: str, limit: int) -> Tuple[str, bool, str]:
    df = await provider.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
    if df is None or df.empty:
        return symbol, False, "empty"

    required = {"open", "high", "low", "close", "volume"}
    missing = sorted(required - set(df.columns))
    if missing:
        return symbol, False, f"missing columns: {missing}"

    return symbol, True, f"rows={len(df)} last={df.index[-1]}"


async def main() -> None:
    provider = MarketDataProvider()
    timeframe = TIMEFRAME
    limit = 200
    print(f"MT5 compatibility check. timeframe={timeframe}, limit={limit}, pairs={len(TRADING_PAIRS)}")

    try:
        tasks = [check_pair(provider, symbol, timeframe, limit) for symbol in TRADING_PAIRS]
        results = await asyncio.gather(*tasks)
    finally:
        await provider.close()

    ok: List[str] = []
    failed: Dict[str, str] = {}

    for symbol, is_ok, details in results:
        if is_ok:
            ok.append(symbol)
            print(f"[OK]   {symbol}: {details}")
        else:
            failed[symbol] = details
            print(f"[FAIL] {symbol}: {details}")

    print("-" * 60)
    print(f"Success: {len(ok)}/{len(TRADING_PAIRS)}")
    if failed:
        print("Failed symbols:")
        for symbol, details in failed.items():
            print(f"  - {symbol}: {details}")


if __name__ == "__main__":
    asyncio.run(main())
