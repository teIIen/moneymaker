from dataclasses import dataclass, field
from typing import Optional, Dict, List
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
    
    # Метрики индикаторов на момент сигнала (для статистики и анализа)
    metrics: Dict[str, any] = field(default_factory=dict)

@dataclass
class MarketAnalysis:
    """
    Объект для передачи полного анализа рынка по конкретной паре.
    """
    symbol: str
    timestamp: datetime
    current_price: float
    trend: str # 'Bullish', 'Bearish', 'Neutral'
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    volume_analysis: Dict[str, any] = field(default_factory=dict)
    signal: Optional[TradeSignal] = None
    reason: str = ""
