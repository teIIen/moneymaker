import pandas as pd
from typing import List, Optional
from core_lib.models import TradeSignal
from strategy_engine.indicators.true_volume import TrueVolumeIndicator
from strategy_engine.indicators.liquidity_levels import LiquidityLevels

class VSAStrategyEngine:
    """
    Ядро стратегии. Анализирует данные, применяет индикаторы и генерирует сигналы.
    """
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.true_volume = TrueVolumeIndicator()
        self.liquidity = LiquidityLevels()
        
    def _apply_math(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Объединяет расчеты всех индикаторов в одном DataFrame
        """
        data = self.true_volume.calculate(df)
        data = self.liquidity.calculate(data, window=5) # Ищем Swing-уровни (5 свечей)
        
        # Определяем близость цены к уровню ликвидности (например, в пределах 0.5% от уровня)
        # Это важно для понимания контекста VSA
        threshold = 0.005 # 0.5%
        
        # Защита от NaN на начальных барах, где уровней еще нет
        has_res = data['recent_resistance'].notna()
        has_sup = data['recent_support'].notna()
        
        data['near_resistance'] = False
        data['near_support'] = False
        
        if data['recent_resistance'].notna().any():
             dist_to_res = abs(data['high'] - data['recent_resistance']) / data['recent_resistance']
             data.loc[has_res, 'near_resistance'] = dist_to_res[has_res] <= threshold
             
        if data['recent_support'].notna().any():
             dist_to_sup = abs(data['low'] - data['recent_support']) / data['recent_support']
             data.loc[has_sup, 'near_support'] = dist_to_sup[has_sup] <= threshold
             
        return data

    def analyze(self, df: pd.DataFrame) -> Optional[TradeSignal]:
        """
        Основной метод анализа последней свечи.
        """
        analyzed_data = self._apply_math(df)
        last_bar = analyzed_data.iloc[-1]
        
        # 1. Снимаем ликвидность сверху + Медвежья кульминация = ШОРТ
        if last_bar['is_climax'] and last_bar['is_bearish'] and last_bar['near_resistance']:
             return TradeSignal(
                symbol=self.symbol,
                action='SELL',
                price=last_bar['close'],
                timestamp=last_bar.name,
                reason="Climax Sell @ Resistance Level -> Short",
                confidence=0.85
            )
             
        # 2. Снимаем ликвидность снизу + Бычья кульминация = ЛОНГ
        if last_bar['is_climax'] and last_bar['is_bullish'] and last_bar['near_support']:
            return TradeSignal(
                symbol=self.symbol,
                action='BUY',
                price=last_bar['close'],
                timestamp=last_bar.name,
                reason="Climax Buy @ Support Level -> Long",
                confidence=0.85
            )
            
        return None
    
    def backtest(self, df: pd.DataFrame) -> List[TradeSignal]:
        """
        Исторический прогон с учетом уровней ликвидности.
        """
        analyzed_data = self._apply_math(df)
        signals = []
        
        for index, row in analyzed_data.iterrows():
            if row['is_climax'] and row['is_bearish'] and row['near_resistance']:
                 signals.append(TradeSignal(
                    symbol=self.symbol,
                    action='SELL',
                    price=row['close'],
                    timestamp=index,
                    reason="Climax Sell @ Resistance Level",
                    confidence=0.85
                ))
            elif row['is_climax'] and row['is_bullish'] and row['near_support']:
                 signals.append(TradeSignal(
                    symbol=self.symbol,
                    action='BUY',
                    price=row['close'],
                    timestamp=index,
                    reason="Climax Buy @ Support Level",
                    confidence=0.85
                ))
                 
        return signals
