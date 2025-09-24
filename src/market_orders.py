"""
Market Orders Module for Binance USDT-M Futures Trading Bot
Handles market buy and sell orders with proper validation and logging.
"""

import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from typing import Dict, Optional
import time
from decimal import Decimal, ROUND_DOWN

class MarketOrderManager:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialize Market Order Manager with Binance client.
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            testnet: Use testnet environment (default: True)
        """
        self.client = Client(api_key, api_secret, testnet=testnet)
        if testnet:
            self.client.API_URL = 'https://testnet.binancefuture.com'
        
        self.logger = logging.getLogger(__name__)
    
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
                            
                            # Check step size with proper precision handling
                            qty_decimal = Decimal(str(quantity))
                            min_qty_decimal = Decimal(str(min_qty))
                            step_size_decimal = Decimal(str(step_size))
                            
                            if step_size_decimal > 0:
                                remainder = (qty_decimal - min_qty_decimal) % step_size_decimal
                                if remainder != 0:
                                    return False
                            
                            return True
            return False
        except Exception as e:
            self.logger.error(f"Error validating quantity for {symbol}: {e}")
            return False
    
    def place_market_order(self, symbol: str, side: str, quantity: float, 
                          reduce_only: bool = False) -> Optional[Dict]:
        """
        Place a market order on Binance Futures.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            side: Order side ('BUY' or 'SELL')
            quantity: Order quantity
            reduce_only: If True, order will only reduce position
            
        Returns:
            Dict: Order response or None if failed
        """
        try:
            # Validate inputs
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol: {symbol}")
            
            if side.upper() not in ['BUY', 'SELL']:
                raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'")
            
            if not self.validate_quantity(symbol, quantity):
                raise ValueError(f"Invalid quantity: {quantity} for symbol {symbol}")
            
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            
            # Log order attempt
            self.logger.info(f"Attempting market {side} order: {quantity} {symbol}")
            
            # Place market order
            order_params = {
                'symbol': symbol.upper(),
                'side': side.upper(),
                'type': 'MARKET',
                'quantity': quantity,
                'timestamp': int(time.time() * 1000)
            }
            
            if reduce_only:
                order_params['reduceOnly'] = True
            
            response = self.client.futures_create_order(**order_params)
            
            # Log successful order
            self.logger.info(f"Market order placed successfully: {response}")
            
            return response
            
        except (BinanceAPIException, BinanceOrderException) as e:
            self.logger.error(f"Binance API error placing market order: {e}")
            return None
        except ValueError as e:
            self.logger.error(f"Validation error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error placing market order: {e}")
            return None
    
    def get_order_status(self, symbol: str, order_id: int) -> Optional[Dict]:
        """
        Get status of a specific order.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID
            
        Returns:
            Dict: Order status or None if failed
        """
        try:
            response = self.client.futures_get_order(
                symbol=symbol.upper(),
                orderId=order_id
            )
            self.logger.info(f"Retrieved order status for {order_id}: {response['status']}")
            return response
        except Exception as e:
            self.logger.error(f"Error getting order status: {e}")
            return None
    
    def cancel_order(self, symbol: str, order_id: int) -> Optional[Dict]:
        """
        Cancel a specific order.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID
            
        Returns:
            Dict: Cancellation response or None if failed
        """
        try:
            response = self.client.futures_cancel_order(
                symbol=symbol.upper(),
                orderId=order_id
            )
            self.logger.info(f"Order {order_id} cancelled successfully")
            return response
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {e}")
            return None