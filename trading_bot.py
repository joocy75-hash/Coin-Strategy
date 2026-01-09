"""
Core Trading Bot Architecture
Implements the main trading bot functionality with risk management
"""

import ccxt
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import json
import os
from pathlib import Path

# Import the API manager we created
try:
    from api_manager import APIKeyManager
except ImportError:
    # If api_manager is not available, create a mock
    class APIKeyManager:
        def __init__(self):
            pass
        def get_binance_credentials(self):
            return {
                'api_key': os.getenv('BINANCE_API_KEY'),
                'api_secret': os.getenv('BINANCE_API_SECRET')
            }

class Position:
    def __init__(self, symbol: str, side: str, size: float, entry_price: float, 
                 stop_loss: float = None, take_profit: float = None):
        self.symbol = symbol
        self.side = side  # 'long' or 'short'
        self.size = size
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.entry_time = datetime.now()
        self.exit_price = None
        self.exit_time = None
        self.pnl = 0.0
        self.is_closed = False

class DailyStats:
    def __init__(self):
        self.trades = 0
        self.wins = 0
        self.losses = 0
        self.total_pnl = 0.0
        self.daily_start = datetime.now().date()
        self.max_drawdown = 0.0
        self.balance_start = 0.0

class TradingBot:
    def __init__(self, symbol: str = "BTCUSDT", 
                 risk_per_trade: float = 0.02,  # 2% risk per trade
                 max_daily_loss: float = 0.05,  # 5% daily loss limit
                 max_daily_trades: int = 5,     # 5 trades per day max
                 timeframe: str = "1h"):
        
        # Initialize API Key Manager
        self.api_manager = APIKeyManager()
        creds = self.api_manager.get_binance_credentials()
        
        # Initialize Binance exchange
        self.exchange = ccxt.binance({
            'apiKey': creds['api_key'],
            'secret': creds['api_secret'],
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })
        
        # Trading parameters
        self.symbol = symbol
        self.timeframe = timeframe
        self.risk_per_trade = risk_per_trade
        self.max_daily_loss = max_daily_loss
        self.max_daily_trades = max_daily_trades
        
        # Position tracking
        self.current_position = None
        self.position_history = []
        
        # Daily statistics
        self.daily_stats = DailyStats()
        
        # Initialize balance tracking
        try:
            balance = self.exchange.fetch_balance()
            self.daily_stats.balance_start = balance['total'].get('USDT', 0)
        except:
            self.daily_stats.balance_start = 0
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('trading_bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"TradingBot initialized for {symbol}")
    
    def get_account_info(self) -> Dict:
        """Get current account information"""
        try:
            balance = self.exchange.fetch_balance()
            positions = self.exchange.fetch_positions() if hasattr(self.exchange, 'fetch_positions') else []
            
            return {
                'balance': balance,
                'positions': positions,
                'timestamp': datetime.now()
            }
        except Exception as e:
            self.logger.error(f"Error fetching account info: {e}")
            return {}
    
    def calculate_position_size(self, entry_price: float, stop_loss_price: float = None) -> float:
        """Calculate position size based on risk management"""
        try:
            balance = self.exchange.fetch_balance()
            available_balance = balance['total'].get('USDT', 0)
            
            if available_balance <= 0:
                self.logger.error("Insufficient balance")
                return 0.0
            
            # Calculate risk amount
            risk_amount = available_balance * self.risk_per_trade
            
            # If stop loss is provided, calculate position size based on stop loss distance
            if stop_loss_price is not None:
                price_diff = abs(entry_price - stop_loss_price)
                if price_diff <= 0:
                    self.logger.warning("Invalid stop loss price")
                    return 0.0
                
                position_size = risk_amount / price_diff
            else:
                # If no stop loss, use a default 2% stop loss calculation
                stop_loss_price = entry_price * 0.98  # 2% stop loss
                price_diff = abs(entry_price - stop_loss_price)
                position_size = risk_amount / price_diff
            
            # Get symbol info to check minimum order size
            symbol_info = self.exchange.fetch_markets_by_id(self.symbol)
            if symbol_info:
                min_amount = symbol_info[0].get('limits', {}).get('amount', {}).get('min', 0.001)
                position_size = max(position_size, min_amount)
            
            # Limit position size to maximum 10% of balance
            max_position_size = (available_balance * 0.1) / entry_price
            position_size = min(position_size, max_position_size)
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def execute_order(self, side: str, size: float, price: float = None, 
                     stop_loss: float = None, take_profit: float = None) -> Optional[Dict]:
        """Execute a market order"""
        try:
            if side.lower() == 'buy':
                order = self.exchange.create_market_buy_order(self.symbol, size)
            elif side.lower() == 'sell':
                order = self.exchange.create_market_sell_order(self.symbol, size)
            else:
                raise ValueError(f"Invalid side: {side}. Use 'buy' or 'sell'")
            
            self.logger.info(f"Order executed: {side.upper()} {size} {self.symbol} @ {order.get('average', 'N/A')}")
            
            # Create position object
            position = Position(
                symbol=self.symbol,
                side='long' if side.lower() == 'buy' else 'short',
                size=size,
                entry_price=order.get('average', price or 0),
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            self.current_position = position
            self.daily_stats.trades += 1
            
            return order
            
        except Exception as e:
            self.logger.error(f"Error executing order: {e}")
            return None
    
    def close_position(self, size: float = None) -> Optional[Dict]:
        """Close current position"""
        if not self.current_position:
            self.logger.warning("No position to close")
            return None
        
        try:
            # Determine size to close
            close_size = size or self.current_position.size
            
            # Execute order to close position
            side = 'sell' if self.current_position.side == 'long' else 'buy'
            order = self.execute_order(side, close_size)
            
            if order:
                # Calculate PnL
                entry_price = self.current_position.entry_price
                exit_price = order.get('average', 0)
                
                if self.current_position.side == 'long':
                    pnl = (exit_price - entry_price) / entry_price
                else:
                    pnl = (entry_price - exit_price) / entry_price
                
                # Update position
                self.current_position.exit_price = exit_price
                self.current_position.exit_time = datetime.now()
                self.current_position.pnl = pnl
                self.current_position.is_closed = True
                
                # Update daily stats
                self.daily_stats.total_pnl += pnl
                if pnl > 0:
                    self.daily_stats.wins += 1
                else:
                    self.daily_stats.losses += 1
                
                # Add to history
                self.position_history.append(self.current_position)
                
                self.logger.info(f"Position closed: PnL {pnl:.2%}")
                
                # Clear current position
                self.current_position = None
                
                return order
            
        except Exception as e:
            self.logger.error(f"Error closing position: {e}")
            return None
    
    def check_risk_limits(self) -> bool:
        """Check if risk limits are exceeded"""
        # Check daily loss limit
        if self.daily_stats.total_pnl <= -self.max_daily_loss:
            self.logger.warning(f"Daily loss limit reached: {self.daily_stats.total_pnl:.2%}")
            return False
        
        # Check daily trade limit
        if self.daily_stats.trades >= self.max_daily_trades:
            self.logger.warning(f"Daily trade limit reached: {self.daily_stats.trades}")
            return False
        
        # Check if it's a new day, reset stats if needed
        if datetime.now().date() != self.daily_stats.daily_start:
            self.logger.info(f"New day detected, resetting daily stats")
            self.daily_stats = DailyStats()
            try:
                balance = self.exchange.fetch_balance()
                self.daily_stats.balance_start = balance['total'].get('USDT', 0)
            except:
                self.daily_stats.balance_start = 0
        
        return True
    
    def get_market_data(self, limit: int = 100) -> pd.DataFrame:
        """Get market data for analysis"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, self.timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Calculate technical indicators
            df['sma_short'] = df['close'].rolling(20).mean()
            df['sma_long'] = df['close'].rolling(50).mean()
            df['ema_short'] = df['close'].ewm(span=12).mean()
            df['ema_long'] = df['close'].ewm(span=26).mean()
            df['rsi'] = self.calculate_rsi(df['close'])
            
            return df
        except Exception as e:
            self.logger.error(f"Error fetching market data: {e}")
            return pd.DataFrame()
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signals(self, df: pd.DataFrame) -> Tuple[bool, bool]:
        """Generate buy/sell signals based on technical indicators"""
        if df.empty or len(df) < 2:
            return False, False
        
        # Simple strategy: SMA crossover with RSI filter
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Buy signal: short SMA crosses above long SMA and RSI < 70 (not overbought)
        buy_signal = (previous['sma_short'] <= previous['sma_long'] and 
                     current['sma_short'] > current['sma_long'] and 
                     current['rsi'] < 70)
        
        # Sell signal: short SMA crosses below long SMA and RSI > 30 (not oversold)
        sell_signal = (previous['sma_short'] >= previous['sma_long'] and 
                      current['sma_short'] < current['sma_long'] and 
                      current['rsi'] > 30)
        
        return buy_signal, sell_signal
    
    def check_stop_loss_take_profit(self) -> bool:
        """Check if stop loss or take profit conditions are met"""
        if not self.current_position:
            return False
        
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            
            # Check stop loss
            if self.current_position.stop_loss:
                if ((self.current_position.side == 'long' and current_price <= self.current_position.stop_loss) or
                    (self.current_position.side == 'short' and current_price >= self.current_position.stop_loss)):
                    self.logger.info(f"Stop loss triggered: {current_price} vs {self.current_position.stop_loss}")
                    self.close_position()
                    return True
            
            # Check take profit
            if self.current_position.take_profit:
                if ((self.current_position.side == 'long' and current_price >= self.current_position.take_profit) or
                    (self.current_position.side == 'short' and current_price <= self.current_position.take_profit)):
                    self.logger.info(f"Take profit triggered: {current_price} vs {self.current_position.take_profit}")
                    self.close_position()
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking stop loss/take profit: {e}")
            return False
    
    def run_strategy(self, strategy_name: str = "SMA_Crossover", 
                     enable_risk_management: bool = True):
        """Run the trading strategy continuously"""
        self.logger.info(f"Starting strategy: {strategy_name}")
        
        while True:
            try:
                # Check risk limits
                if enable_risk_management and not self.check_risk_limits():
                    self.logger.info("Risk limits exceeded, pausing strategy")
                    time.sleep(60)  # Wait 1 minute before checking again
                    continue
                
                # Check if stop loss/take profit conditions are met
                if self.current_position:
                    if self.check_stop_loss_take_profit():
                        continue  # Position was closed, continue to next iteration
                
                # Get market data
                df = self.get_market_data()
                if df.empty:
                    self.logger.warning("Failed to get market data")
                    time.sleep(30)
                    continue
                
                # Generate signals
                buy_signal, sell_signal = self.generate_signals(df)
                
                # Execute strategy based on signals
                if buy_signal and not self.current_position:
                    # Calculate stop loss and take profit
                    current_price = df['close'].iloc[-1]
                    stop_loss = current_price * 0.98  # 2% stop loss
                    take_profit = current_price * 1.05  # 5% take profit
                    
                    # Calculate position size
                    position_size = self.calculate_position_size(current_price, stop_loss)
                    
                    if position_size > 0:
                        self.logger.info(f"Buy signal detected, executing order")
                        self.execute_order('buy', position_size, stop_loss=stop_loss, take_profit=take_profit)
                
                elif sell_signal and self.current_position and self.current_position.side == 'long':
                    # Close long position on sell signal
                    self.logger.info(f"Sell signal detected, closing position")
                    self.close_position()
                
                # Wait before next iteration (respect API limits)
                time.sleep(10)
                
            except KeyboardInterrupt:
                self.logger.info("Strategy interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Error in strategy loop: {e}")
                time.sleep(30)  # Wait 30 seconds before retrying
    
    def get_performance_metrics(self) -> Dict:
        """Get performance metrics"""
        total_trades = len(self.position_history)
        winning_trades = sum(1 for pos in self.position_history if pos.pnl > 0) if self.position_history else 0
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        total_pnl = sum(pos.pnl for pos in self.position_history) if self.position_history else 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'daily_stats': {
                'trades': self.daily_stats.trades,
                'wins': self.daily_stats.wins,
                'losses': self.daily_stats.losses,
                'total_pnl': self.daily_stats.total_pnl
            }
        }

# Example usage
if __name__ == "__main__":
    bot = TradingBot()
    print("Trading bot initialized successfully")
    print("Account info:", bot.get_account_info())
    print("Performance metrics:", bot.get_performance_metrics())
