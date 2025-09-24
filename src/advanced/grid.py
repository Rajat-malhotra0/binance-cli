"""
Grid Orders Module for Binance USDT-M Futures Trading Bot
Handles automated grid trading strategy with buy-low/sell-high within price ranges.
"""

import logging
import time
import threading
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from typing import Dict, Optional, List, Callable
import math

class GridOrderManager:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialize Grid Order Manager with Binance client.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet environment (default: True)
        """
        self.client = Client(api_key, api_secret, testnet=testnet)
        if testnet:
            self.client.API_URL = 'https://testnet.binancefuture.com'
        
        self.logger = logging.getLogger(__name__)
        self.active_grids = {}
        self.stop_flags = {}
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if symbol exists and is tradeable.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            exchange_info = self.client.futures_exchange_info()
            symbols = [s['symbol'] for s in exchange_info['symbols'] 
                      if s['status'] == 'TRADING']
            return symbol.upper() in symbols
        except Exception as e:
            self.logger.error(f"Error validating symbol {symbol}: {e}")
            return False
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """
        Get symbol trading information.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dict: Symbol info or None if failed
        """
        try:
            exchange_info = self.client.futures_exchange_info()
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol.upper():
                    symbol_info = {
                        'symbol': s['symbol'],
                        'status': s['status'],
                        'baseAsset': s['baseAsset'],
                        'quoteAsset': s['quoteAsset']
                    }
                    
                    # Extract filters
                    for filter_item in s['filters']:
                        if filter_item['filterType'] == 'LOT_SIZE':
                            symbol_info['minQty'] = float(filter_item['minQty'])
                            symbol_info['maxQty'] = float(filter_item['maxQty'])
                            symbol_info['stepSize'] = float(filter_item['stepSize'])
                        elif filter_item['filterType'] == 'PRICE_FILTER':
                            symbol_info['minPrice'] = float(filter_item['minPrice'])
                            symbol_info['maxPrice'] = float(filter_item['maxPrice'])
                            symbol_info['tickSize'] = float(filter_item['tickSize'])
                    
                    return symbol_info
            return None
        except Exception as e:
            self.logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            float: Current price or None if failed
        """
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol.upper())
            return float(ticker['price'])
        except Exception as e:
            self.logger.error(f"Error getting current price for {symbol}: {e}")
            return None
    
    def calculate_grid_levels(self, center_price: float, price_range_percent: float,
                            grid_count: int, symbol_info: Dict) -> List[float]:
        """
        Calculate grid price levels.
        
        Args:
            center_price: Center price for the grid
            price_range_percent: Price range as percentage (e.g., 0.1 for 10%)
            grid_count: Number of grid levels
            symbol_info: Symbol trading information
            
        Returns:
            List[float]: List of grid price levels
        """
        try:
            tick_size = symbol_info['tickSize']
            
            # Calculate price range
            price_range = center_price * price_range_percent
            min_price = center_price - price_range
            max_price = center_price + price_range
            
            # Calculate grid step
            if grid_count <= 1:
                return [center_price]
            
            price_step = (max_price - min_price) / (grid_count - 1)
            
            # Generate grid levels
            grid_levels = []
            for i in range(grid_count):
                price = min_price + i * price_step
                # Round to tick size
                price = math.floor(price / tick_size) * tick_size
                grid_levels.append(price)
            
            return sorted(set(grid_levels))  # Remove duplicates and sort
            
        except Exception as e:
            self.logger.error(f"Error calculating grid levels: {e}")
            return []
    
    def place_grid_orders(self, symbol: str, center_price: float = None,
                         price_range_percent: float = 0.05, grid_count: int = 10,
                         order_quantity: float = None, total_investment: float = None,
                         callback: Callable = None) -> Optional[str]:
        """
        Place grid orders for automated trading.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            center_price: Center price for grid (current price if None)
            price_range_percent: Price range as percentage (default: 5%)
            grid_count: Number of grid levels (default: 10)
            order_quantity: Quantity per order (auto-calculated if None)
            total_investment: Total investment amount (used if order_quantity is None)
            callback: Callback function for order updates
            
        Returns:
            str: Grid ID or None if failed
        """
        try:
            # Validate inputs
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol: {symbol}")
            
            if price_range_percent <= 0 or price_range_percent >= 1:
                raise ValueError("Price range percent must be between 0 and 1")
            
            if grid_count < 2:
                raise ValueError("Grid count must be at least 2")
            
            # Get symbol info
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                raise ValueError(f"Cannot get symbol info for {symbol}")
            
            # Get current price if not provided
            if not center_price:
                center_price = self.get_current_price(symbol)
                if not center_price:
                    raise ValueError("Cannot get current price")
            
            # Calculate order quantity if not provided
            if not order_quantity:
                if not total_investment:
                    raise ValueError("Either order_quantity or total_investment must be provided")
                order_quantity = total_investment / (grid_count * center_price)
            
            # Validate quantity
            min_qty = symbol_info['minQty']
            step_size = symbol_info['stepSize']
            
            if order_quantity < min_qty:
                raise ValueError(f"Order quantity {order_quantity} is below minimum {min_qty}")
            
            # Round quantity to step size
            order_quantity = math.floor(order_quantity / step_size) * step_size
            
            # Calculate grid levels
            grid_levels = self.calculate_grid_levels(
                center_price, price_range_percent, grid_count, symbol_info
            )
            
            if len(grid_levels) < 2:
                raise ValueError("Failed to generate valid grid levels")
            
            # Generate unique grid ID
            grid_id = f"GRID_{symbol}_{int(time.time())}"
            
            # Initialize grid tracking
            self.active_grids[grid_id] = {
                'symbol': symbol,
                'center_price': center_price,
                'price_range_percent': price_range_percent,
                'grid_levels': grid_levels,
                'order_quantity': order_quantity,
                'buy_orders': {},
                'sell_orders': {},
                'executed_trades': [],
                'total_profit': 0,
                'status': 'ACTIVE',
                'callback': callback,
                'start_time': time.time()
            }
            
            self.stop_flags[grid_id] = False
            
            # Log grid order start
            self.logger.info(f"Starting grid trading {grid_id} for {symbol}")
            self.logger.info(f"Grid levels: {len(grid_levels)}, Quantity per order: {order_quantity}")
            
            # Place initial grid orders
            self._place_initial_grid_orders(grid_id)
            
            # Start grid monitoring in separate thread
            thread = threading.Thread(target=self._monitor_grid, args=(grid_id,))
            thread.daemon = True
            thread.start()
            
            return grid_id
            
        except ValueError as e:
            self.logger.error(f"Validation error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error starting grid: {e}")
            return None
    
    def _place_initial_grid_orders(self, grid_id: str):
        """
        Place initial buy and sell orders for the grid.
        
        Args:
            grid_id: Grid ID
        """
        try:
            grid = self.active_grids[grid_id]
            symbol = grid['symbol']
            center_price = grid['center_price']
            grid_levels = grid['grid_levels']
            order_quantity = grid['order_quantity']
            
            # Place buy orders below center price
            for price in grid_levels:
                if price < center_price:
                    try:
                        order = self.client.futures_create_order(
                            symbol=symbol.upper(),
                            side='BUY',
                            type='LIMIT',
                            quantity=order_quantity,
                            price=price,
                            timeInForce='GTC',
                            timestamp=int(time.time() * 1000)
                        )
                        
                        grid['buy_orders'][price] = order
                        self.logger.info(f"Grid buy order placed at {price}: {order['orderId']}")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to place buy order at {price}: {e}")
            
            # Place sell orders above center price
            for price in grid_levels:
                if price > center_price:
                    try:
                        order = self.client.futures_create_order(
                            symbol=symbol.upper(),
                            side='SELL',
                            type='LIMIT',
                            quantity=order_quantity,
                            price=price,
                            timeInForce='GTC',
                            timestamp=int(time.time() * 1000)
                        )
                        
                        grid['sell_orders'][price] = order
                        self.logger.info(f"Grid sell order placed at {price}: {order['orderId']}")
                        
                    except Exception as e:
                        self.logger.error(f"Failed to place sell order at {price}: {e}")
            
        except Exception as e:
            self.logger.error(f"Error placing initial grid orders: {e}")
    
    def _monitor_grid(self, grid_id: str):
        """
        Monitor grid orders and replace filled orders.
        
        Args:
            grid_id: Grid ID
        """
        try:
            grid = self.active_grids[grid_id]
            symbol = grid['symbol']
            callback = grid['callback']
            
            while not self.stop_flags.get(grid_id, False):
                try:
                    # Check buy orders
                    for price, order in list(grid['buy_orders'].items()):
                        order_status = self.client.futures_get_order(
                            symbol=symbol.upper(),
                            orderId=order['orderId']
                        )
                        
                        if order_status['status'] == 'FILLED':
                            # Buy order filled, place sell order above
                            self._handle_buy_fill(grid_id, price, order_status)
                    
                    # Check sell orders
                    for price, order in list(grid['sell_orders'].items()):
                        order_status = self.client.futures_get_order(
                            symbol=symbol.upper(),
                            orderId=order['orderId']
                        )
                        
                        if order_status['status'] == 'FILLED':
                            # Sell order filled, place buy order below
                            self._handle_sell_fill(grid_id, price, order_status)
                    
                    # Callback for grid update
                    if callback:
                        callback(grid_id, 'UPDATE', {
                            'active_buy_orders': len(grid['buy_orders']),
                            'active_sell_orders': len(grid['sell_orders']),
                            'total_profit': grid['total_profit']
                        })
                    
                    # Wait before next check
                    time.sleep(5)
                    
                except Exception as e:
                    self.logger.error(f"Error monitoring grid {grid_id}: {e}")
                    time.sleep(10)
            
            self.logger.info(f"Grid monitoring stopped for {grid_id}")
            
        except Exception as e:
            self.logger.error(f"Error in grid monitoring thread: {e}")
    
    def _handle_buy_fill(self, grid_id: str, price: float, order_status: Dict):
        """Handle filled buy order."""
        try:
            grid = self.active_grids[grid_id]
            symbol = grid['symbol']
            order_quantity = grid['order_quantity']
            grid_levels = grid['grid_levels']
            
            # Remove filled buy order
            del grid['buy_orders'][price]
            
            # Record trade
            trade = {
                'side': 'BUY',
                'price': price,
                'quantity': float(order_status['executedQty']),
                'time': order_status['updateTime'],
                'order_id': order_status['orderId']
            }
            grid['executed_trades'].append(trade)
            
            # Find next sell level
            higher_levels = [p for p in grid_levels if p > price]
            if higher_levels:
                sell_price = min(higher_levels)
                
                # Place sell order
                try:
                    sell_order = self.client.futures_create_order(
                        symbol=symbol.upper(),
                        side='SELL',
                        type='LIMIT',
                        quantity=order_quantity,
                        price=sell_price,
                        timeInForce='GTC',
                        timestamp=int(time.time() * 1000)
                    )
                    
                    grid['sell_orders'][sell_price] = sell_order
                    self.logger.info(f"Grid sell order placed at {sell_price} after buy fill at {price}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to place sell order after buy fill: {e}")
            
        except Exception as e:
            self.logger.error(f"Error handling buy fill: {e}")
    
    def _handle_sell_fill(self, grid_id: str, price: float, order_status: Dict):
        """Handle filled sell order."""
        try:
            grid = self.active_grids[grid_id]
            symbol = grid['symbol']
            order_quantity = grid['order_quantity']
            grid_levels = grid['grid_levels']
            
            # Remove filled sell order
            del grid['sell_orders'][price]
            
            # Record trade
            trade = {
                'side': 'SELL',
                'price': price,
                'quantity': float(order_status['executedQty']),
                'time': order_status['updateTime'],
                'order_id': order_status['orderId']
            }
            grid['executed_trades'].append(trade)
            
            # Calculate profit (simplified)
            if len(grid['executed_trades']) >= 2:
                # Find matching buy trade
                buy_trades = [t for t in grid['executed_trades'] if t['side'] == 'BUY' and t['price'] < price]
                if buy_trades:
                    latest_buy = max(buy_trades, key=lambda x: x['time'])
                    profit = (price - latest_buy['price']) * trade['quantity']
                    grid['total_profit'] += profit
            
            # Find next buy level
            lower_levels = [p for p in grid_levels if p < price]
            if lower_levels:
                buy_price = max(lower_levels)
                
                # Place buy order
                try:
                    buy_order = self.client.futures_create_order(
                        symbol=symbol.upper(),
                        side='BUY',
                        type='LIMIT',
                        quantity=order_quantity,
                        price=buy_price,
                        timeInForce='GTC',
                        timestamp=int(time.time() * 1000)
                    )
                    
                    grid['buy_orders'][buy_price] = buy_order
                    self.logger.info(f"Grid buy order placed at {buy_price} after sell fill at {price}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to place buy order after sell fill: {e}")
            
        except Exception as e:
            self.logger.error(f"Error handling sell fill: {e}")
    
    def stop_grid(self, grid_id: str) -> bool:
        """
        Stop grid trading and cancel all open orders.
        
        Args:
            grid_id: Grid ID
            
        Returns:
            bool: True if stopped successfully
        """
        try:
            if grid_id not in self.active_grids:
                self.logger.error(f"Grid {grid_id} not found")
                return False
            
            grid = self.active_grids[grid_id]
            symbol = grid['symbol']
            
            # Set stop flag
            self.stop_flags[grid_id] = True
            
            # Cancel all buy orders
            for price, order in grid['buy_orders'].items():
                try:
                    self.client.futures_cancel_order(
                        symbol=symbol.upper(),
                        orderId=order['orderId']
                    )
                    self.logger.info(f"Cancelled buy order at {price}")
                except Exception as e:
                    self.logger.error(f"Failed to cancel buy order at {price}: {e}")
            
            # Cancel all sell orders
            for price, order in grid['sell_orders'].items():
                try:
                    self.client.futures_cancel_order(
                        symbol=symbol.upper(),
                        orderId=order['orderId']
                    )
                    self.logger.info(f"Cancelled sell order at {price}")
                except Exception as e:
                    self.logger.error(f"Failed to cancel sell order at {price}: {e}")
            
            # Update grid status
            grid['status'] = 'STOPPED'
            grid['stop_time'] = time.time()
            
            self.logger.info(f"Grid {grid_id} stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping grid {grid_id}: {e}")
            return False
    
    def get_grid_status(self, grid_id: str) -> Optional[Dict]:
        """
        Get status of a grid trading session.
        
        Args:
            grid_id: Grid ID
            
        Returns:
            Dict: Grid status or None if not found
        """
        try:
            if grid_id not in self.active_grids:
                return None
            
            grid = self.active_grids[grid_id].copy()
            # Remove callback function from response
            if 'callback' in grid:
                del grid['callback']
            
            return grid
            
        except Exception as e:
            self.logger.error(f"Error getting grid status: {e}")
            return None