import pandas as pd
from typing import List
from dataclasses import dataclass
from risk_management.manager import OrderInstruction

@dataclass
class TradeResult:
    """Результат завершенной сделки."""
    symbol: str
    action: str
    entry_price: float
    exit_price: float
    pnl_usd: float  # Profit and Loss в долларах
    status: str     # 'TP', 'SL' или 'OPEN'

class PaperTrader:
    """
    Симулятор торгов.
    Проходит по историческим данным вперед от момента сигнала и проверяет, 
    какой уровень был задет первым: Stop-Loss или Take-Profit.
    """
    def __init__(self):
        self.history: List[TradeResult] = []
        
    def simulate_trade(self, df: pd.DataFrame, signal_index: pd.Timestamp, instruction: OrderInstruction) -> TradeResult:
        """
        Симулирует одну сделку.
        df: полный DataFrame со свечами
        signal_index: время, когда был получен сигнал
        instruction: параметры сделки от Risk-менеджера
        """
        # Берем все свечи ПОСЛЕ сигнала
        future_data = df.loc[signal_index:].iloc[1:] # iloc[1:] чтобы не смотреть на свечу сигнала
        
        for index, row in future_data.iterrows():
            high = row['high']
            low = row['low']
            
            if instruction.action == 'BUY':
                # Для лонга: проверяем, задел ли лоу свечи стоп, или хай - тейк
                # (В реальной жизни внутри одной свечи может быть задето и то и то, 
                # для безопасности в бэктесте мы считаем, что если задето оба, то это SL)
                if low <= instruction.stop_loss:
                    return TradeResult(
                        symbol=instruction.symbol,
                        action=instruction.action,
                        entry_price=instruction.entry_price,
                        exit_price=instruction.stop_loss,
                        pnl_usd=-instruction.risk_usd,
                        status='SL'
                    )
                elif high >= instruction.take_profit:
                    # Прибыль = Риск * Risk/Reward ratio
                    reward_usd = (instruction.take_profit - instruction.entry_price) * instruction.position_size_coins
                    return TradeResult(
                        symbol=instruction.symbol,
                        action=instruction.action,
                        entry_price=instruction.entry_price,
                        exit_price=instruction.take_profit,
                        pnl_usd=reward_usd,
                        status='TP'
                    )
                    
            elif instruction.action == 'SELL':
                # Для шорта: стоп сверху (high), тейк снизу (low)
                if high >= instruction.stop_loss:
                    return TradeResult(
                        symbol=instruction.symbol,
                        action=instruction.action,
                        entry_price=instruction.entry_price,
                        exit_price=instruction.stop_loss,
                        pnl_usd=-instruction.risk_usd,
                        status='SL'
                    )
                elif low <= instruction.take_profit:
                    reward_usd = (instruction.entry_price - instruction.take_profit) * instruction.position_size_coins
                    return TradeResult(
                        symbol=instruction.symbol,
                        action=instruction.action,
                        entry_price=instruction.entry_price,
                        exit_price=instruction.take_profit,
                        pnl_usd=reward_usd,
                        status='TP'
                    )
        
        # Если сделка не закрылась до конца доступных данных
        return TradeResult(
            symbol=instruction.symbol,
            action=instruction.action,
            entry_price=instruction.entry_price,
            exit_price=future_data.iloc[-1]['close'] if not future_data.empty else instruction.entry_price,
            pnl_usd=0.0,
            status='OPEN'
        )
