import pandas as pd
import numpy as np

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
        
        # Initialize columns for all active levels
        data['all_active_resistances'] = [[] for _ in range(len(data))]
        data['all_active_supports'] = [[] for _ in range(len(data))]

        # Store all confirmed levels with their index of confirmation
        confirmed_resistances = [] # List of (value, index_confirmed)
        confirmed_supports = []    # List of (value, index_confirmed)

        for i in range(len(data)):
            current_row = data.iloc[i]
            row_idx = data.index[i]
            current_close = current_row['close']
            current_high = current_row['high']
            current_low = current_row['low']

            # Add newly confirmed levels
            if pd.notna(current_row['conf_res']):
                confirmed_resistances.append((current_row['conf_res'], i))
            if pd.notna(current_row['conf_sup']):
                confirmed_supports.append((current_row['conf_sup'], i))

            # Filter active resistances: only keep resistances that have not been broken by current_high
            active_resistances_values = []
            new_confirmed_resistances = []
            for res_val, res_idx in confirmed_resistances:
                # A resistance is broken if the current high is above it
                if current_high > res_val:
                    pass # This resistance is broken
                else:
                    new_confirmed_resistances.append((res_val, res_idx))
                    active_resistances_values.append(res_val)
            confirmed_resistances = new_confirmed_resistances

            # Filter active supports: only keep supports that have not been broken by current_low
            active_supports_values = []
            new_confirmed_supports = []
            for sup_val, sup_idx in confirmed_supports:
                # A support is broken if the current low is below it
                if current_low < sup_val:
                    pass # This support is broken
                else:
                    new_confirmed_supports.append((sup_val, sup_idx))
                    active_supports_values.append(sup_val)
            confirmed_supports = new_confirmed_supports

            # Sort for consistent order
            active_resistances_values.sort() # Ascending, so lowest resistance is first
            active_supports_values.sort(reverse=True) # Descending, so highest support is first

            data.at[row_idx, 'all_active_resistances'] = active_resistances_values[:]
            data.at[row_idx, 'all_active_supports'] = active_supports_values[:]

            # Update recent_resistance and recent_support based on active levels
            # The closest active resistance above current price
            closest_res_above = [res for res in active_resistances_values if res > current_close]
            data.at[row_idx, 'recent_resistance'] = closest_res_above[0] if closest_res_above else np.nan

            # The closest active support below current price
            closest_sup_below = [sup for sup in active_supports_values if sup < current_close]
            data.at[row_idx, 'recent_support'] = closest_sup_below[0] if closest_sup_below else np.nan

        return data
