import pandas as pd
from typing import List, Optional, Dict
from core_lib.models import TradeSignal
from strategy_engine.indicators.true_volume import TrueVolumeIndicator
from strategy_engine.indicators.liquidity_levels import LiquidityLevels
from strategy_engine.indicators.kraya import KrayaIndicator
from core_lib.logger import setup_logger

class VSAStrategyEngine:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.log = setup_logger("StrategyEngine")
        self.log.info(f"Инициализация VSA Strategy Engine для {symbol}")
        
        self.true_volume = TrueVolumeIndicator()
        self.liquidity = LiquidityLevels()
        self.kraya = KrayaIndicator()
        
    def _apply_math(self, df: pd.DataFrame) -> pd.DataFrame:
        data = self.true_volume.calculate(df)
        data = self.liquidity.calculate(data, window=5)
        data = self.kraya.calculate(data, window=20, deviation_multiplier=2.0)
        
        threshold = 0.005 # 0.5%
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

    def _extract_metrics(self, row: pd.Series) -> Dict[str, any]:
        return {
            "vol_ratio": round(row['vol_ratio'], 2) if not pd.isna(row['vol_ratio']) else 0.0,
            "is_climax": bool(row['is_climax']),
            "near_resistance": bool(row['near_resistance']),
            "near_support": bool(row['near_support']),
            "is_overbought": bool(row['is_overbought']),
            "is_oversold": bool(row['is_oversold'])
        }

    def analyze(self, df: pd.DataFrame) -> Optional[TradeSignal]:
        analyzed_data = self._apply_math(df)
        last_bar = analyzed_data.iloc[-1]
        
        metrics = self._extract_metrics(last_bar)
        
        if last_bar['is_climax'] and last_bar['is_bearish'] and last_bar['near_resistance'] and last_bar['is_overbought']:
             signal = TradeSignal(
                symbol=self.symbol, action='SELL', price=last_bar['close'],
                timestamp=last_bar.name, reason="Climax Sell @ Resistance + Overbought -> Short",
                confidence=0.9, metrics=metrics
            )
             self.log.info(f"Сгенерирован сигнал: {signal}")
             return signal
             
        if last_bar['is_climax'] and last_bar['is_bullish'] and last_bar['near_support'] and last_bar['is_oversold']:
            signal = TradeSignal(
                symbol=self.symbol, action='BUY', price=last_bar['close'],
                timestamp=last_bar.name, reason="Climax Buy @ Support + Oversold -> Long",
                confidence=0.9, metrics=metrics
            )
            self.log.info(f"Сгенерирован сигнал: {signal}")
            return signal
            
        return None
    
    def backtest(self, df: pd.DataFrame) -> List[TradeSignal]:
        self.log.info(f"Запуск исторического бэктеста на {len(df)} свечах...")
        analyzed_data = self._apply_math(df)
        signals = []
        
        for index, row in analyzed_data.iterrows():
            metrics = self._extract_metrics(row)
            if row['is_climax'] and row['is_bearish'] and row['near_resistance'] and row['is_overbought']:
                 signals.append(TradeSignal(
                    symbol=self.symbol, action='SELL', price=row['close'], timestamp=index,
                    reason="Climax Sell @ Resistance + Overbought", confidence=0.9, metrics=metrics
                ))
            elif row['is_climax'] and row['is_bullish'] and row['near_support'] and row['is_oversold']:
                 signals.append(TradeSignal(
                    symbol=self.symbol, action='BUY', price=row['close'], timestamp=index,
                    reason="Climax Buy @ Support + Oversold", confidence=0.9, metrics=metrics
                ))
        self.log.info(f"Бэктест завершен. Найдено сигналов: {len(signals)}")
        return signals
