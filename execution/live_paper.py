from dataclasses import dataclass
from typing import List, Optional
from risk_management.manager import OrderInstruction
from core_lib.logger import setup_logger

@dataclass
class ActivePosition:
    symbol: str
    action: str  
    entry_price: float
    position_size_usd: float
    position_size_coins: float
    stop_loss: float
    take_profit: float
    current_pnl_usd: float = 0.0

class LivePaperTrader:
    def __init__(self, start_balance: float = 1000.0):
        self.log = setup_logger("LivePaperTrader")
        self.balance = start_balance
        self.active_positions: List[ActivePosition] = []
        self.trade_history = []
        self.log.info(f"Инициализация LivePaperTrader. Стартовый баланс: ${start_balance}")
        
    def open_position(self, instruction: OrderInstruction) -> bool:
        for pos in self.active_positions:
            if pos.symbol == instruction.symbol:
                self.log.warning(f"Позиция по {instruction.symbol} уже открыта.")
                return False  
                
        new_pos = ActivePosition(
            symbol=instruction.symbol, action=instruction.action, entry_price=instruction.entry_price,
            position_size_usd=instruction.position_size_usd, position_size_coins=instruction.position_size_coins,
            stop_loss=instruction.stop_loss, take_profit=instruction.take_profit
        )
        self.active_positions.append(new_pos)
        self.log.info(f"Открыта новая виртуальная позиция: {instruction.action} {instruction.symbol}")
        return True

    def update_prices(self, symbol: str, current_price: float, high: float, low: float) -> List[dict]:
        closed_trades = []
        positions_to_keep = []
        
        for pos in self.active_positions:
            if pos.symbol != symbol:
                positions_to_keep.append(pos)
                continue
                
            is_closed = False
            close_reason = ""
            exit_price = 0.0
            
            if pos.action == 'BUY':
                if low <= pos.stop_loss:
                    is_closed = True; close_reason = 'SL'; exit_price = pos.stop_loss
                elif high >= pos.take_profit:
                    is_closed = True; close_reason = 'TP'; exit_price = pos.take_profit
                pos.current_pnl_usd = (current_price - pos.entry_price) * pos.position_size_coins
                
            elif pos.action == 'SELL':
                if high >= pos.stop_loss:
                    is_closed = True; close_reason = 'SL'; exit_price = pos.stop_loss
                elif low <= pos.take_profit:
                    is_closed = True; close_reason = 'TP'; exit_price = pos.take_profit
                pos.current_pnl_usd = (pos.entry_price - current_price) * pos.position_size_coins

            if is_closed:
                pnl = (exit_price - pos.entry_price) * pos.position_size_coins if pos.action == 'BUY' else (pos.entry_price - exit_price) * pos.position_size_coins
                self.balance += pnl
                
                trade_result = {
                    'symbol': pos.symbol, 'action': pos.action, 'entry_price': pos.entry_price,
                    'exit_price': exit_price, 'pnl_usd': pnl, 'reason': close_reason
                }
                closed_trades.append(trade_result)
                self.trade_history.append(trade_result)
                self.log.info(f"Позиция {pos.symbol} закрыта по {close_reason}. PNL: ${pnl:.2f}. Новый баланс: ${self.balance:.2f}")
            else:
                positions_to_keep.append(pos)
                
        self.active_positions = positions_to_keep
        return closed_trades
