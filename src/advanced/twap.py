"""
TWAP (Time-Weighted Average Price) Orders Module for Binance USDT-M Futures Trading Bot
Handles TWAP strategy by splitting large orders into smaller chunks over time.
"""

import logging
import time
import threading
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from typing import Dict, Optional, List, Callable
import math
from datetime import datetime, timedelta

class TWAPOrderManager:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialize TWAP Order Manager with Binance client.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet environment (default: True)
        """
        self.client = Client(api_key, api_secret, testnet=testnet)
        if testnet:
            self.client.API_URL = 'https://testnet.binancefuture.com'
        
        self.logger = logging.getLogger(__name__)
        self.active_twap_orders = {}
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
    
    def validate_quantity(self, symbol: str, quantity: float) -> bool:
        """
        Validate quantity against symbol's lot size requirements.
        
        Args:
            symbol: Trading symbol
            quantity: Order quantity
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            exchange_info = self.client.futures_exchange_info()
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol.upper():
                    for filter_item in s['filters']:
                        if filter_item['filterType'] == 'LOT_SIZE':
                            min_qty = float(filter_item['minQty'])
                            max_qty = float(filter_item['maxQty'])
                            step_size = float(filter_item['stepSize'])
                            
                            if quantity < min_qty or quantity > max_qty:
                                return False
                            
                            # Check step size
                            if (quantity - min_qty) % step_size != 0:
                                return False
                            
                            return True
            return False
        except Exception as e:
            self.logger.error(f"Error validating quantity for {symbol}: {e}")
            return False
    
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
    
    def calculate_order_chunks(self, total_quantity: float, num_orders: int, 
                             symbol: str) -> List[float]:
        """
        Calculate order chunk sizes ensuring they meet exchange requirements.
        
        Args:
            total_quantity: Total quantity to split
            num_orders: Number of orders to split into
            symbol: Trading symbol
            
        Returns:
            List[float]: List of order chunk sizes
        """
        try:
            # Get step size for the symbol
            exchange_info = self.client.futures_exchange_info()
            step_size = None
            min_qty = None
            
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol.upper():
                    for filter_item in s['filters']:
                        if filter_item['filterType'] == 'LOT_SIZE':
                            step_size = float(filter_item['stepSize'])
                            min_qty = float(filter_item['minQty'])
                            break
                    break
            
            if not step_size or not min_qty:
                raise ValueError(f"Cannot get lot size info for {symbol}")
            
            # Calculate base chunk size
            base_chunk = total_quantity / num_orders
            
            # Round to step size
            chunks = []
            remaining_qty = total_quantity
            
            for i in range(num_orders - 1):
                # Round down to nearest step size
                chunk = math.floor(base_chunk / step_size) * step_size
                chunk = max(chunk, min_qty)  # Ensure minimum quantity
                chunks.append(chunk)
                remaining_qty -= chunk
            
            # Last chunk gets remaining quantity (rounded to step size)
            last_chunk = math.floor(remaining_qty / step_size) * step_size
            if last_chunk >= min_qty:
                chunks.append(last_chunk)
            else:
                # If last chunk too small, add to previous chunk
                if chunks:
                    chunks[-1] += remaining_qty
            
            return chunks
            
        except Exception as e:
            self.logger.error(f"Error calculating order chunks: {e}")
            return []
    
    def place_twap_order(self, symbol: str, side: str, total_quantity: float,
                        duration_minutes: int, num_orders: int = None,
                        order_type: str = 'MARKET', limit_price: float = None,
                        max_price_deviation: float = 0.01,
                        callback: Callable = None) -> Optional[str]:
        """
        Place a TWAP order by splitting large order into smaller chunks over time.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            side: Order side ('BUY' or 'SELL')
            total_quantity: Total quantity to execute
            duration_minutes: Duration to spread orders over (in minutes)
            num_orders: Number of orders to split into (auto-calculated if None)
            order_type: Order type ('MARKET' or 'LIMIT')
            limit_price: Limit price for limit orders
            max_price_deviation: Maximum price deviation from TWAP (0.01 = 1%)
            callback: Callback function for order updates
            
        Returns:
            str: TWAP order ID or None if failed
        """
        try:
            # Validate inputs
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol: {symbol}")
            
            if side.upper() not in ['BUY', 'SELL']:
                raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'")
            
            if not self.validate_quantity(symbol, total_quantity):
                raise ValueError(f"Invalid total quantity: {total_quantity}")
            
            if duration_minutes <= 0:
                raise ValueError("Duration must be positive")
            
            if order_type not in ['MARKET', 'LIMIT']:
                raise ValueError("Order type must be 'MARKET' or 'LIMIT'")
            
            if order_type == 'LIMIT' and not limit_price:
                raise ValueError("Limit price required for limit orders")
            
            # Auto-calculate number of orders if not provided
            if not num_orders:
                # Rule of thumb: 1 order per minute, minimum 2, maximum 20
                num_orders = max(2, min(20, duration_minutes))
            
            # Calculate order chunks
            chunks = self.calculate_order_chunks(total_quantity, num_orders, symbol)
            if not chunks:
                raise ValueError("Failed to calculate order chunks")
            
            # Calculate interval between orders
            interval_seconds = (duration_minutes * 60) / len(chunks)
            
            # Generate unique TWAP order ID
            twap_id = f"TWAP_{symbol}_{int(time.time())}"
            
            # Initialize TWAP order tracking
            self.active_twap_orders[twap_id] = {
                'symbol': symbol,
                'side': side,
                'total_quantity': total_quantity,
                'chunks': chunks,
                'executed_quantity': 0,
                'order_type': order_type,
                'limit_price': limit_price,
                'max_price_deviation': max_price_deviation,
                'interval_seconds': interval_seconds,
                'start_time': datetime.now(),
                'orders': [],
                'status': 'ACTIVE',
                'callback': callback
            }
            
            self.stop_flags[twap_id] = False
            
            # Log TWAP order start
            self.logger.info(f"Starting TWAP order {twap_id}: {total_quantity} {symbol}")
            self.logger.info(f"Split into {len(chunks)} orders over {duration_minutes} minutes")
            
            # Start TWAP execution in separate thread
            thread = threading.Thread(target=self._execute_twap, args=(twap_id,))
            thread.daemon = True
            thread.start()
            
            return twap_id
            
        except ValueError as e:
            self.logger.error(f"Validation error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error starting TWAP order: {e}")
            return None
    
    def _execute_twap(self, twap_id: str):
        """
        Execute TWAP order in background thread.
        
        Args:
            twap_id: TWAP order ID
        """
        try:
            twap_order = self.active_twap_orders[twap_id]
            symbol = twap_order['symbol']
            side = twap_order['side']
            chunks = twap_order['chunks']
            order_type = twap_order['order_type']
            limit_price = twap_order['limit_price']
            max_deviation = twap_order['max_price_deviation']
            interval = twap_order['interval_seconds']
            callback = twap_order['callback']
            
            # Get initial price for TWAP calculation
            initial_price = self.get_current_price(symbol)
            if not initial_price:
                raise ValueError("Cannot get initial price")
            
            total_value = 0
            total_quantity = 0
            
            for i, chunk_qty in enumerate(chunks):
                if self.stop_flags.get(twap_id, False):
                    self.logger.info(f"TWAP order {twap_id} stopped by user")
                    break
                
                try:
                    # Get current price
                    current_price = self.get_current_price(symbol)
                    if not current_price:
                        self.logger.error(f"Cannot get current price for chunk {i+1}")
                        continue
                    
                    # Check price deviation if specified
                    if max_deviation > 0:
                        price_change = abs(current_price - initial_price) / initial_price
                        if price_change > max_deviation:
                            self.logger.warning(f"Price deviation {price_change:.2%} exceeds limit {max_deviation:.2%}")
                            if callback:
                                callback(twap_id, 'PRICE_DEVIATION', {
                                    'current_price': current_price,
                                    'initial_price': initial_price,
                                    'deviation': price_change
                                })
                    
                    # Place individual order
                    if order_type == 'MARKET':
                        order_result = self._place_market_chunk(symbol, side, chunk_qty)
                    else:  # LIMIT
                        order_result = self._place_limit_chunk(symbol, side, chunk_qty, limit_price)
                    
                    if order_result:
                        # Update tracking
                        twap_order['orders'].append(order_result)
                        executed_qty = float(order_result.get('executedQty', chunk_qty))
                        twap_order['executed_quantity'] += executed_qty
                        
                        # Update TWAP calculation
                        if order_type == 'MARKET' and 'fills' in order_result:
                            for fill in order_result['fills']:
                                fill_qty = float(fill['qty'])
                                fill_price = float(fill['price'])
                                total_value += fill_qty * fill_price
                                total_quantity += fill_qty
                        
                        self.logger.info(f"TWAP chunk {i+1}/{len(chunks)} executed: {executed_qty} {symbol}")
                        
                        # Callback for order completion
                        if callback:
                            avg_price = total_value / total_quantity if total_quantity > 0 else 0
                            callback(twap_id, 'CHUNK_COMPLETED', {
                                'chunk_number': i + 1,
                                'chunk_quantity': executed_qty,
                                'total_executed': twap_order['executed_quantity'],
                                'average_price': avg_price
                            })
                    
                    # Wait for next order (except for last order)
                    if i < len(chunks) - 1:
                        time.sleep(interval)
                
                except Exception as e:
                    self.logger.error(f"Error executing TWAP chunk {i+1}: {e}")
                    continue
            
            # Mark TWAP order as completed
            twap_order['status'] = 'COMPLETED'
            twap_order['end_time'] = datetime.now()
            
            # Calculate final TWAP
            if total_quantity > 0:
                final_twap = total_value / total_quantity
                twap_order['twap_price'] = final_twap
                self.logger.info(f"TWAP order {twap_id} completed. Final TWAP: {final_twap}")
                
                if callback:
                    callback(twap_id, 'COMPLETED', {
                        'total_executed': twap_order['executed_quantity'],
                        'twap_price': final_twap,
                        'duration': twap_order['end_time'] - twap_order['start_time']
                    })
            
        except Exception as e:
            self.logger.error(f"Error executing TWAP order {twap_id}: {e}")
            if twap_id in self.active_twap_orders:
                self.active_twap_orders[twap_id]['status'] = 'ERROR'
    
    def _place_market_chunk(self, symbol: str, side: str, quantity: float) -> Optional[Dict]:
        """Place a market order chunk."""
        try:
            return self.client.futures_create_order(
                symbol=symbol.upper(),
                side=side.upper(),
                type='MARKET',
                quantity=quantity,
                timestamp=int(time.time() * 1000)
            )
        except Exception as e:
            self.logger.error(f"Error placing market chunk: {e}")
            return None
    
    def _place_limit_chunk(self, symbol: str, side: str, quantity: float, 
                          price: float) -> Optional[Dict]:
        """Place a limit order chunk."""
        try:
            return self.client.futures_create_order(
                symbol=symbol.upper(),
                side=side.upper(),
                type='LIMIT',
                quantity=quantity,
                price=price,
                timeInForce='GTC',
                timestamp=int(time.time() * 1000)
            )
        except Exception as e:
            self.logger.error(f"Error placing limit chunk: {e}")
            return None
    
    def stop_twap_order(self, twap_id: str) -> bool:
        """
        Stop a running TWAP order.
        
        Args:
            twap_id: TWAP order ID
            
        Returns:
            bool: True if stopped successfully
        """
        try:
            if twap_id not in self.active_twap_orders:
                self.logger.error(f"TWAP order {twap_id} not found")
                return False
            
            self.stop_flags[twap_id] = True
            self.active_twap_orders[twap_id]['status'] = 'STOPPED'
            
            self.logger.info(f"TWAP order {twap_id} stop requested")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping TWAP order {twap_id}: {e}")
            return False
    
    def get_twap_status(self, twap_id: str) -> Optional[Dict]:
        """
        Get status of a TWAP order.
        
        Args:
            twap_id: TWAP order ID
            
        Returns:
            Dict: TWAP order status or None if not found
        """
        try:
            if twap_id not in self.active_twap_orders:
                return None
            
            twap_order = self.active_twap_orders[twap_id].copy()
            # Remove callback function from response
            if 'callback' in twap_order:
                del twap_order['callback']
            
            return twap_order
            
        except Exception as e:
            self.logger.error(f"Error getting TWAP status: {e}")
            return None
    
    def list_active_twap_orders(self) -> List[str]:
        """
        List all active TWAP order IDs.
        
        Returns:
            List[str]: List of active TWAP order IDs
        """
        return [twap_id for twap_id, order in self.active_twap_orders.items()
                if order['status'] == 'ACTIVE']