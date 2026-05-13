import pandas as pd

class LiquidityLevels:
    """
    Индикатор ликвидности (аналог SmokeFX PROfile).
    Ищет пулы ликвидности - Swing Highs (сопротивление) и Swing Lows (поддержка), 
    за которыми участники рынка прячут свои стоп-лоссы.
    """
    
    @staticmethod
    def calculate(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
        """
        Ищет локальные максимумы и минимумы.
        window = 5 означает, что мы ищем свечу, которая выше 5 свечей слева и 5 справа.
        Внимание: чтобы избежать заглядывания в будущее (Lookahead Bias), 
        уровень становится известным (подтверждается) только спустя `window` свечей.
        """
        data = df.copy()
        
        # 1. Ищем фракталы (свинги)
        data['is_swing_high'] = True
        data['is_swing_low'] = True
        
        for i in range(1, window + 1):
            data['is_swing_high'] &= (data['high'] > data['high'].shift(i)) & (data['high'] > data['high'].shift(-i))
            data['is_swing_low'] &= (data['low'] < data['low'].shift(i)) & (data['low'] < data['low'].shift(-i))
            
        data['is_swing_high'] = data['is_swing_high'].fillna(False)
        data['is_swing_low'] = data['is_swing_low'].fillna(False)
        
        # 2. Фиксируем уровни, смещая их в будущее на `window` баров
        # Это симуляция реального времени: мы не можем знать в моменте, 
        # что это был High, пока не пройдут следующие 5 падающих свечей.
        data['conf_res'] = data['high'].where(data['is_swing_high']).shift(window)
        data['conf_sup'] = data['low'].where(data['is_swing_low']).shift(window)
        
        # 3. Протягиваем (forward fill) значения, чтобы знать актуальный уровень на любой текущей свече
        data['recent_resistance'] = data['conf_res'].ffill()
        data['recent_support'] = data['conf_sup'].ffill()
        
        return data
