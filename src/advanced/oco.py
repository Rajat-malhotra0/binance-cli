"""
OCO (One-Cancels-the-Other) Orders Module for Binance USDT-M Futures Trading Bot
Handles OCO orders combining stop-loss and take-profit orders.
"""

import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
from typing import Dict, Optional, Tuple
import time
from decimal import Decimal, ROUND_DOWN

class OCOOrderManager:
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialize OCO Order Manager with Binance client.
        
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
    
    def validate_price(self, symbol: str, price: float) -> bool:
        """
        Validate price against symbol's price filter requirements.
        
        Args:
            symbol: Trading symbol
            price: Order price
            
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            exchange_info = self.client.futures_exchange_info()
            for s in exchange_info['symbols']:
                if s['symbol'] == symbol.upper():
                    for filter_item in s['filters']:
                        if filter_item['filterType'] == 'PRICE_FILTER':
                            min_price = float(filter_item['minPrice'])
                            max_price = float(filter_item['maxPrice'])
                            tick_size = float(filter_item['tickSize'])
                            
                            if price < min_price or price > max_price:
                                return False
                            
                            # Check tick size with proper precision handling
                            price_decimal = Decimal(str(price))
                            min_price_decimal = Decimal(str(min_price))
                            tick_size_decimal = Decimal(str(tick_size))
                            
                            if tick_size_decimal > 0:
                                remainder = (price_decimal - min_price_decimal) % tick_size_decimal
                                if remainder != 0:
                                    return False
                            
                            return True
            return False
        except Exception as e:
            self.logger.error(f"Error validating price for {symbol}: {e}")
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
    
    def place_oco_order(self, symbol: str, side: str, quantity: float,
                       take_profit_price: float, stop_loss_price: float,
                       time_in_force: str = 'GTC') -> Optional[Tuple[Dict, Dict]]:
        """
        Place an OCO order (Take Profit + Stop Loss).
        
        Note: Binance Futures doesn't have native OCO orders, so we simulate
        by placing two conditional orders that monitor each other.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            side: Order side ('BUY' or 'SELL')
            quantity: Order quantity
            take_profit_price: Take profit target price
            stop_loss_price: Stop loss trigger price
            time_in_force: Time in force ('GTC', 'IOC', 'FOK')
            
        Returns:
            Tuple[Dict, Dict]: (take_profit_order, stop_loss_order) or None if failed
        """
        try:
            # Validate inputs
            if not self.validate_symbol(symbol):
                raise ValueError(f"Invalid symbol: {symbol}")
            
            if side.upper() not in ['BUY', 'SELL']:
                raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'")
            
            if not self.validate_quantity(symbol, quantity):
                raise ValueError(f"Invalid quantity: {quantity} for symbol {symbol}")
            
            if not self.validate_price(symbol, take_profit_price):
                raise ValueError(f"Invalid take profit price: {take_profit_price}")
            
            if not self.validate_price(symbol, stop_loss_price):
                raise ValueError(f"Invalid stop loss price: {stop_loss_price}")
            
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            
            # Get current price to validate order logic
            current_price = self.get_current_price(symbol)
            if not current_price:
                raise ValueError("Cannot get current market price")
            
            # Validate price relationships based on side
            if side.upper() == 'BUY':
                # For buy orders (closing short position)
                if take_profit_price >= current_price:
                    raise ValueError("Take profit price must be below current price for buy orders")
                if stop_loss_price <= current_price:
                    raise ValueError("Stop loss price must be above current price for buy orders")
            else:  # SELL
                # For sell orders (closing long position)
                if take_profit_price <= current_price:
                    raise ValueError("Take profit price must be above current price for sell orders")
                if stop_loss_price >= current_price:
                    raise ValueError("Stop loss price must be below current price for sell orders")
            
            # Log OCO order attempt
            self.logger.info(f"Attempting OCO {side} order: {quantity} {symbol}")
            self.logger.info(f"Take Profit: {take_profit_price}, Stop Loss: {stop_loss_price}")
            
            # Place take profit order (limit order)
            tp_order_params = {
                'symbol': symbol.upper(),
                'side': side.upper(),
                'type': 'LIMIT',
                'quantity': quantity,
                'price': take_profit_price,
                'timeInForce': time_in_force,
                'reduceOnly': True,
                'timestamp': int(time.time() * 1000)
            }
            
            take_profit_order = self.client.futures_create_order(**tp_order_params)
            self.logger.info(f"Take profit order placed: {take_profit_order['orderId']}")
            
            # Place stop loss order (stop market order)
            sl_order_params = {
                'symbol': symbol.upper(),
                'side': side.upper(),
                'type': 'STOP_MARKET',
                'quantity': quantity,
                'stopPrice': stop_loss_price,
                'reduceOnly': True,
                'timestamp': int(time.time() * 1000)
            }
            
            stop_loss_order = self.client.futures_create_order(**sl_order_params)
            self.logger.info(f"Stop loss order placed: {stop_loss_order['orderId']}")
            
            # Log successful OCO order
            self.logger.info(f"OCO order placed successfully")
            
            return (take_profit_order, stop_loss_order)
            
        except (BinanceAPIException, BinanceOrderException) as e:
            self.logger.error(f"Binance API error placing OCO order: {e}")
            # If one order succeeded but the other failed, cancel the first one
            try:
                if 'take_profit_order' in locals() and take_profit_order:
                    self.client.futures_cancel_order(
                        symbol=symbol.upper(),
                        orderId=take_profit_order['orderId']
                    )
                    self.logger.info("Cancelled take profit order due to stop loss failure")
            except:
                pass
            return None
        except ValueError as e:
            self.logger.error(f"Validation error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error placing OCO order: {e}")
            return None
    
    def cancel_oco_order(self, symbol: str, tp_order_id: int, sl_order_id: int) -> bool:
        """
        Cancel both orders in an OCO pair.
        
        Args:
            symbol: Trading symbol
            tp_order_id: Take profit order ID
            sl_order_id: Stop loss order ID
            
        Returns:
            bool: True if both orders cancelled successfully
        """
        try:
            tp_cancelled = False
            sl_cancelled = False
            
            # Cancel take profit order
            try:
                self.client.futures_cancel_order(
                    symbol=symbol.upper(),
                    orderId=tp_order_id
                )
                tp_cancelled = True
                self.logger.info(f"Take profit order {tp_order_id} cancelled")
            except Exception as e:
                self.logger.error(f"Failed to cancel take profit order {tp_order_id}: {e}")
            
            # Cancel stop loss order
            try:
                self.client.futures_cancel_order(
                    symbol=symbol.upper(),
                    orderId=sl_order_id
                )
                sl_cancelled = True
                self.logger.info(f"Stop loss order {sl_order_id} cancelled")
            except Exception as e:
                self.logger.error(f"Failed to cancel stop loss order {sl_order_id}: {e}")
            
            return tp_cancelled and sl_cancelled
            
        except Exception as e:
            self.logger.error(f"Error cancelling OCO order: {e}")
            return False
    
    def get_oco_status(self, symbol: str, tp_order_id: int, sl_order_id: int) -> Optional[Dict]:
        """
        Get status of both orders in an OCO pair.
        
        Args:
            symbol: Trading symbol
            tp_order_id: Take profit order ID
            sl_order_id: Stop loss order ID
            
        Returns:
            Dict: Status of both orders or None if failed
        """
        try:
            tp_status = self.client.futures_get_order(
                symbol=symbol.upper(),
                orderId=tp_order_id
            )
            
            sl_status = self.client.futures_get_order(
                symbol=symbol.upper(),
                orderId=sl_order_id
            )
            
            return {
                'take_profit': tp_status,
                'stop_loss': sl_status,
                'oco_status': self._determine_oco_status(tp_status, sl_status)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting OCO status: {e}")
            return None
    
    def _determine_oco_status(self, tp_order: Dict, sl_order: Dict) -> str:
        """
        Determine overall OCO status based on individual order statuses.
        
        Args:
            tp_order: Take profit order details
            sl_order: Stop loss order details
            
        Returns:
            str: Overall OCO status
        """
        tp_status = tp_order['status']
        sl_status = sl_order['status']
        
        if tp_status == 'FILLED':
            return 'TAKE_PROFIT_FILLED'
        elif sl_status == 'FILLED':
            return 'STOP_LOSS_FILLED'
        elif tp_status == 'CANCELED' and sl_status == 'CANCELED':
            return 'BOTH_CANCELED'
        elif tp_status in ['NEW', 'PARTIALLY_FILLED'] and sl_status in ['NEW', 'PARTIALLY_FILLED']:
            return 'ACTIVE'
        else:
            return 'UNKNOWN'