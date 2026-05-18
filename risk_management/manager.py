from dataclasses import dataclass
from core_lib.models import TradeSignal
import numpy as np


@dataclass
class OrderInstruction:
    symbol: str
    action: str
    entry_price: float
    position_size_usd: float
    position_size_coins: float
    stop_loss: float
    take_profit: float
    risk_usd: float


class RiskManager:
    def __init__(
        self,
        account_balance_usd: float = 1000.0,
        risk_per_trade_percent: float = 1.0,
        risk_reward_ratio: float = 2.0,
    ):
        self.account_balance_usd = account_balance_usd
        self.risk_per_trade_percent = risk_per_trade_percent
        self.risk_reward_ratio = risk_reward_ratio

    def _calculate_stop_loss(self, signal: TradeSignal, percent: float = 0.01) -> float:
        if signal.action == "BUY":
            return signal.price * (1.0 - percent)
        if signal.action == "SELL":
            return signal.price * (1.0 + percent)
        return signal.price

    @staticmethod
    def _to_float(value):
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def validate_and_size(self, signal: TradeSignal) -> OrderInstruction:
        risk_usd = self.account_balance_usd * (self.risk_per_trade_percent / 100.0)

        # Extract all active liquidity levels
        all_active_resistances = signal.metrics.get("all_active_resistances", [])
        all_active_supports = signal.metrics.get("all_active_supports", [])

        # Determine Stop-Loss price
        stop_loss_price = self._calculate_stop_loss(signal) # Default SL
        
        recent_support = self._to_float(signal.metrics.get("recent_support"))
        recent_resistance = self._to_float(signal.metrics.get("recent_resistance"))

        if signal.action == "BUY":
            # If there's a recent support below entry, use it as SL
            if recent_support is not None and recent_support < signal.price:
                stop_loss_price = recent_support
        elif signal.action == "SELL":
            # If there's a recent resistance above entry, use it as SL
            if recent_resistance is not None and recent_resistance > signal.price:
                stop_loss_price = recent_resistance

        # Ensure stop_loss_price is not too close to entry_price
        stop_loss_distance_pct = abs(signal.price - stop_loss_price) / signal.price
        if stop_loss_distance_pct <= 0.0001:  # Minimum 0.01% distance to avoid division by zero or tiny stops
            stop_loss_price = self._calculate_stop_loss(signal, percent=0.005) # Fallback to a small percentage
            stop_loss_distance_pct = abs(signal.price - stop_loss_price) / signal.price
            if stop_loss_distance_pct <= 0.0001: # If still too small, something is wrong, return None or raise error
                raise ValueError("Calculated stop loss is too close to entry price.")


        # Calculate position size based on risk_usd and stop_loss_distance
        position_size_usd = risk_usd / stop_loss_distance_pct
        if position_size_usd > self.account_balance_usd:
            position_size_usd = self.account_balance_usd
            risk_usd = position_size_usd * stop_loss_distance_pct # Adjust risk_usd if position size is capped

        position_size_coins = position_size_usd / signal.price

        # Determine Take-Profit price
        take_profit_price = None

        if signal.action == "BUY":
            # Look for the next resistance level as TP
            for res_level in all_active_resistances:
                if res_level > signal.price: # Resistance must be above entry for BUY
                    potential_rr = (res_level - signal.price) / (signal.price - stop_loss_price)
                    if potential_rr >= self.risk_reward_ratio:
                        take_profit_price = res_level
                        break # Found a suitable TP level
            
            # Fallback if no suitable liquidity level found
            if take_profit_price is None:
                distance_to_tp = (signal.price - stop_loss_price) * self.risk_reward_ratio
                take_profit_price = signal.price + distance_to_tp

        elif signal.action == "SELL":
            # Look for the next support level as TP
            # all_active_supports are sorted descending, so we iterate to find the first one below entry
            for sup_level in all_active_supports:
                if sup_level < signal.price: # Support must be below entry for SELL
                    potential_rr = (signal.price - sup_level) / (stop_loss_price - signal.price)
                    if potential_rr >= self.risk_reward_ratio:
                        take_profit_price = sup_level
                        break # Found a suitable TP level
            
            # Fallback if no suitable liquidity level found
            if take_profit_price is None:
                distance_to_tp = (stop_loss_price - signal.price) * self.risk_reward_ratio
                take_profit_price = signal.price - distance_to_tp
        
        # Ensure TP is not too close to entry or SL
        if signal.action == "BUY" and take_profit_price <= signal.price:
            distance_to_tp = (signal.price - stop_loss_price) * self.risk_reward_ratio
            take_profit_price = signal.price + distance_to_tp
        elif signal.action == "SELL" and take_profit_price >= signal.price:
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
            risk_usd=round(risk_usd, 2),
        )
