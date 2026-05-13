import pandas as pd

class KrayaIndicator:
    """
    Индикатор SmokeFX Kraya (Края).
    Определяет сильную перекупленность и перепроданность на основе отклонения цены 
    от скользящей средней (Mean Reversion) и волатильности (ATR/Bollinger-like логика).
    """
    
    @staticmethod
    def calculate(df: pd.DataFrame, window: int = 20, deviation_multiplier: float = 2.0) -> pd.DataFrame:
        """
        Рассчитывает "Края" рынка.
        Использует логику каналов Кельтнера или Полос Боллинджера для понимания экстремумов.
        """
        data = df.copy()
        
        # 1. Базовая линия (Средняя цена)
        data['kraya_basis'] = data['close'].rolling(window=window).mean()
        
        # 2. Волатильность (Стандартное отклонение)
        data['kraya_dev'] = data['close'].rolling(window=window).std()
        
        # 3. Верхний и нижний края (Верхняя и нижняя границы канала)
        data['kraya_upper'] = data['kraya_basis'] + (data['kraya_dev'] * deviation_multiplier)
        data['kraya_lower'] = data['kraya_basis'] - (data['kraya_dev'] * deviation_multiplier)
        
        # 4. Флаги перекупленности / перепроданности (Выход за края)
        data['is_overbought'] = data['high'] >= data['kraya_upper']
        data['is_oversold'] = data['low'] <= data['kraya_lower']
        
        return data
