import pandas as pd
import numpy as np

class TrueVolumeIndicator:
    """
    Математическая реализация индикатора SmokeFX True Volumes.
    В основе VSA (Volume Spread Analysis) лежит анализ спреда свечи (High - Low)
    и ее объема для понимания усилий покупателей и продавцов.
    """
    
    @staticmethod
    def calculate(df: pd.DataFrame) -> pd.DataFrame:
        """
        Принимает DataFrame с колонками OHLCV.
        Возвращает DataFrame с добавленными колонками для True Volume.
        """
        # Создаем копию, чтобы не менять исходные данные (чистые функции)
        data = df.copy()
        
        # 1. Спред свечи (разница между максимумом и минимумом)
        data['spread'] = data['high'] - data['low']
        
        # Избегаем деления на ноль, если спред равен нулю (доджи на неликвидах)
        # Заменяем 0 на очень маленькое число. Избегаем inplace для совместимости с pandas 2.x
        data['spread'] = data['spread'].replace(0, np.nan)
        data['spread'] = data['spread'].fillna(1e-8)
        
        # 2. Объем на единицу спреда (усилие / результат)
        # Помогает понять, насколько легко цена проходила расстояние
        data['vol_per_spread'] = data['volume'] / data['spread']
        
        # 3. Нормализация объема (чтобы сравнивать разные таймфреймы/монеты)
        # Используем скользящее среднее объема для определения "аномальных" баров
        data['vol_sma_20'] = data['volume'].rolling(window=20).mean()
        data['vol_ratio'] = data['volume'] / data['vol_sma_20']
        
        # 4. Простейшая классификация бара (Бычий / Медвежий)
        data['is_bullish'] = data['close'] > data['open']
        data['is_bearish'] = data['close'] < data['open']
        
        # 5. Определение кульминации (Climax) 
        # Если объем аномально высокий (например, > 2x от среднего)
        data['is_climax'] = data['vol_ratio'] > 2.0
        
        # 6. Определение недостатка спроса/предложения (No Demand / No Supply)
        # Низкий объем на узком спреде
        data['is_low_vol'] = data['vol_ratio'] < 0.5
        
        return data
