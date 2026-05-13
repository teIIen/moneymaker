from dataclasses import dataclass
from core_lib.models import TradeSignal

@dataclass
class OrderInstruction:
    """
    Инструкция для исполнения ордера. Выдается риск-менеджером.
    """
    symbol: str
    action: str
    entry_price: float
    position_size_usd: float
    position_size_coins: float
    stop_loss: float
    take_profit: float
    risk_usd: float

class RiskManager:
    """
    Модуль управления рисками.
    Отвечает за расчет размера позиции и установку Stop-Loss / Take-Profit.
    """
    def __init__(self, account_balance_usd: float = 1000.0, risk_per_trade_percent: float = 1.0, risk_reward_ratio: float = 2.0):
        self.account_balance_usd = account_balance_usd
        self.risk_per_trade_percent = risk_per_trade_percent
        self.risk_reward_ratio = risk_reward_ratio # Соотношение Прибыль/Риск (Например, 1 к 2)
        
    def _calculate_stop_loss(self, signal: TradeSignal, atr_or_percentage: float = 0.01) -> float:
        """
        Рассчитывает уровень стоп-лосса. 
        Пока используем фиксированный процент от цены входа (например, 1%).
        В будущем будем ставить стоп за тень свечи или уровень ликвидности.
        """
        if signal.action == 'BUY':
            return signal.price * (1.0 - atr_or_percentage)
        elif signal.action == 'SELL':
            return signal.price * (1.0 + atr_or_percentage)
        return signal.price

    def validate_and_size(self, signal: TradeSignal) -> OrderInstruction:
        """
        Принимает торговый сигнал и превращает его в готовую инструкцию для биржи
        с рассчитанными рисками.
        """
        # 1. Считаем, сколько $ мы готовы потерять в этой сделке
        risk_usd = self.account_balance_usd * (self.risk_per_trade_percent / 100.0)
        
        # 2. Определяем цену стоп-лосса
        stop_loss_price = self._calculate_stop_loss(signal)
        
        # 3. Считаем расстояние до стопа в процентах
        stop_loss_distance_pct = abs(signal.price - stop_loss_price) / signal.price
        
        # 4. Position Sizing: (Сумма риска) / (Расстояние до стопа)
        # Пример: Готовы потерять 10$. Стоп в 1% от цены. Значит позиция = 1000$.
        position_size_usd = risk_usd / stop_loss_distance_pct
        
        # Проверка на превышение баланса (если торгуем без плечей)
        if position_size_usd > self.account_balance_usd:
            # Если позиция больше баланса, значит стоп-лосс слишком короткий для нашего депозита без плеча.
            # Для крипты тут обычно вступают в игру фьючерсы с плечом. 
            # Пока ограничим размер позиции балансом:
            position_size_usd = self.account_balance_usd
            # Пересчитаем реальный риск, если обрезали позицию
            risk_usd = position_size_usd * stop_loss_distance_pct
            
        position_size_coins = position_size_usd / signal.price
        
        # 5. Считаем Take-Profit на основе Risk:Reward Ratio
        if signal.action == 'BUY':
            distance_to_tp = (signal.price - stop_loss_price) * self.risk_reward_ratio
            take_profit_price = signal.price + distance_to_tp
        else: # SELL
            distance_to_tp = (stop_loss_price - signal.price) * self.risk_reward_ratio
            take_profit_price = signal.price - distance_to_tp

        return OrderInstruction(
            symbol=signal.symbol,
            action=signal.action,
            entry_price=signal.price,
            position_size_usd=round(position_size_usd, 2),
            position_size_coins=position_size_coins,
            stop_loss=round(stop_loss_price, 2),
            take_profit=round(take_profit_price, 2),
            risk_usd=round(risk_usd, 2)
        )
