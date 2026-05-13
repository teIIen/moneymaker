from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class TradeSignal:
    """
    Стандартный объект передачи торговых сигналов между модулями системы.
    """
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    price: float
    timestamp: datetime
    confidence: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""
