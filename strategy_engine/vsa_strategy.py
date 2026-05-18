import pandas as pd
from typing import List, Optional, Dict, Any
from core_lib.models import TradeSignal
from strategy_engine.indicators.true_volume import TrueVolumeIndicator
from strategy_engine.indicators.liquidity_levels import LiquidityLevels
from strategy_engine.indicators.kraya import KrayaIndicator
from core_lib.logger import setup_logger
from config.settings import USE_KRAYA_FILTER

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
        data['ema_50'] = data['close'].ewm(span=50, adjust=False).mean()
        data['ema_200'] = data['close'].ewm(span=200, adjust=False).mean()
        data['trend'] = 'neutral'
        data.loc[(data['ema_50'] > data['ema_200']) & (data['close'] > data['ema_200']), 'trend'] = 'bullish'
        data.loc[(data['ema_50'] < data['ema_200']) & (data['close'] < data['ema_200']), 'trend'] = 'bearish'
        
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

    def _extract_metrics(self, row: pd.Series, sentiment_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        metrics = {
            "vol_ratio": round(row['vol_ratio'], 2) if not pd.isna(row['vol_ratio']) else 0.0,
            "is_climax": bool(row['is_climax']),
            "near_resistance": bool(row['near_resistance']),
            "near_support": bool(row['near_support']),
            "is_overbought": bool(row['is_overbought']),
            "is_oversold": bool(row['is_oversold']),
            "recent_resistance": float(row['recent_resistance']) if not pd.isna(row['recent_resistance']) else None,
            "recent_support": float(row['recent_support']) if not pd.isna(row['recent_support']) else None,
            "trend": str(row['trend']),
            "ema_50": float(row['ema_50']) if not pd.isna(row['ema_50']) else None,
            "ema_200": float(row['ema_200']) if not pd.isna(row['ema_200']) else None,
            "all_active_resistances": row['all_active_resistances'] if 'all_active_resistances' in row and isinstance(row['all_active_resistances'], list) else [],
            "all_active_supports": row['all_active_supports'] if 'all_active_supports' in row and isinstance(row['all_active_supports'], list) else [],
        }
        if sentiment_data:
            metrics["news_sentiment"] = sentiment_data.get("compound_avg", 0.0)
            metrics["news_article_count"] = sentiment_data.get("article_count", 0)
        else:
            metrics["news_sentiment"] = 0.0 # Default to neutral if no data
            metrics["news_article_count"] = 0
        return metrics

    def analyze(self, df: pd.DataFrame, sentiment_data: Optional[Dict[str, Any]] = None) -> Optional[TradeSignal]:
        analyzed_data = self._apply_math(df)
        last_bar = analyzed_data.iloc[-1]
        
        metrics = self._extract_metrics(last_bar, sentiment_data)
        
        if (
            last_bar['trend'] != 'bullish'
            and last_bar['is_climax']
            and last_bar['is_bearish']
            and last_bar['near_resistance']
            and ((not USE_KRAYA_FILTER) or last_bar['is_overbought'])
        ):
             signal = TradeSignal(
                symbol=self.symbol, action='SELL', price=last_bar['close'],
                timestamp=last_bar.name, reason="Climax Sell @ Resistance + Overbought -> Short",
                confidence=0.9, metrics=metrics
            )
             self.log.info(f"Сгенерирован сигнал: {signal}")
             return signal
             
        if (
            last_bar['trend'] != 'bearish'
            and last_bar['is_climax']
            and last_bar['is_bullish']
            and last_bar['near_support']
            and ((not USE_KRAYA_FILTER) or last_bar['is_oversold'])
        ):
            signal = TradeSignal(
                symbol=self.symbol, action='BUY', price=last_bar['close'],
                timestamp=last_bar.name, reason="Climax Buy @ Support + Oversold -> Long",
                confidence=0.9, metrics=metrics
            )
            self.log.info(f"Сгенерирован сигнал: {signal}")
            return signal
            
        return None
    
    def backtest(self, df: pd.DataFrame, sentiment_data: Optional[Dict[str, Any]] = None) -> List[TradeSignal]:
        self.log.info(f"Запуск исторического бэктеста на {len(df)} свечах...")
        analyzed_data = self._apply_math(df)
        signals = []
        
        for index, row in analyzed_data.iterrows():
            # For backtesting, sentiment_data would typically be historical,
            # but for now, we'll just pass it if provided (e.g., for a single test case)
            metrics = self._extract_metrics(row, sentiment_data)
            if (
                row['trend'] != 'bullish'
                and row['is_climax']
                and row['is_bearish']
                and row['near_resistance']
                and ((not USE_KRAYA_FILTER) or row['is_overbought'])
            ):
                 signals.append(TradeSignal(
                    symbol=self.symbol, action='SELL', price=row['close'], timestamp=index,
                    reason="Climax Sell @ Resistance + Overbought", confidence=0.9, metrics=metrics
                ))
            elif (
                row['trend'] != 'bearish'
                and row['is_climax']
                and row['is_bullish']
                and row['near_support']
                and ((not USE_KRAYA_FILTER) or row['is_oversold'])
            ):
                 signals.append(TradeSignal(
                    symbol=self.symbol, action='BUY', price=row['close'], timestamp=index,
                    reason="Climax Buy @ Support + Oversold", confidence=0.9, metrics=metrics
                ))
        self.log.info(f"Бэктест завершен. Найдено сигналов: {len(signals)}")
        return signals
