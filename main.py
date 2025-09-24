#!/usr/bin/env python3
"""
Binance USDT-M Futures Trading Bot
CLI-based trading bot with support for multiple order types.
"""

import os
import sys
import argparse
import logging
import time
from typing import Optional
import json

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'src', 'advanced'))

from market_orders import MarketOrderManager
from limit_orders import LimitOrderManager
from advanced.oco import OCOOrderManager
from advanced.twap import TWAPOrderManager
from advanced.grid import GridOrderManager

def setup_logging():
    """Set up structured logging for the bot."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def get_api_credentials():
    """Get API credentials from environment variables."""
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        print("Error: Please set BINANCE_API_KEY and BINANCE_API_SECRET environment variables")
        print("You can set them by running:")
        print("export BINANCE_API_KEY='your_api_key'")
        print("export BINANCE_API_SECRET='your_api_secret'")
        return None, None
    
    return api_key, api_secret

def print_order_result(result: Optional[dict], order_type: str):
    """Print formatted order result."""
    if result:
        print(f"\n✅ {order_type} Order Placed Successfully!")
        print(f"Order ID: {result.get('orderId')}")
        print(f"Symbol: {result.get('symbol')}")
        print(f"Side: {result.get('side')}")
        print(f"Quantity: {result.get('origQty')}")
        if 'price' in result:
            print(f"Price: {result.get('price')}")
        print(f"Status: {result.get('status')}")
        print(f"Client Order ID: {result.get('clientOrderId')}")
    else:
        print(f"\n❌ Failed to place {order_type} order. Check logs for details.")

def handle_market_order(args, logger):
    """Handle market order placement."""
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    market_manager = MarketOrderManager(api_key, api_secret, testnet=True)
    
    print(f"\nPlacing Market {args.side.upper()} Order...")
    print(f"Symbol: {args.symbol}")
    print(f"Quantity: {args.quantity}")
    
    result = market_manager.place_market_order(
        symbol=args.symbol,
        side=args.side,
        quantity=args.quantity,
        reduce_only=args.reduce_only
    )
    
    print_order_result(result, "Market")

def handle_limit_order(args, logger):
    """Handle limit order placement."""
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    limit_manager = LimitOrderManager(api_key, api_secret, testnet=True)
    
    print(f"\nPlacing Limit {args.side.upper()} Order...")
    print(f"Symbol: {args.symbol}")
    print(f"Quantity: {args.quantity}")
    print(f"Price: {args.price}")
    print(f"Time in Force: {args.time_in_force}")
    
    result = limit_manager.place_limit_order(
        symbol=args.symbol,
        side=args.side,
        quantity=args.quantity,
        price=args.price,
        time_in_force=args.time_in_force,
        reduce_only=args.reduce_only
    )
    
    print_order_result(result, "Limit")

def handle_order_status(args, logger):
    """Handle order status check."""
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    market_manager = MarketOrderManager(api_key, api_secret, testnet=True)
    
    print(f"\nChecking order status...")
    print(f"Symbol: {args.symbol}")
    print(f"Order ID: {args.order_id}")
    
    result = market_manager.get_order_status(args.symbol, args.order_id)
    
    if result:
        print("\n📊 Order Status:")
        print(f"Order ID: {result.get('orderId')}")
        print(f"Symbol: {result.get('symbol')}")
        print(f"Side: {result.get('side')}")
        print(f"Type: {result.get('type')}")
        print(f"Status: {result.get('status')}")
        print(f"Original Quantity: {result.get('origQty')}")
        print(f"Executed Quantity: {result.get('executedQty')}")
        if 'price' in result:
            print(f"Price: {result.get('price')}")
        if 'avgPrice' in result and float(result.get('avgPrice', 0)) > 0:
            print(f"Average Price: {result.get('avgPrice')}")
        print(f"Time in Force: {result.get('timeInForce')}")
        print(f"Update Time: {result.get('updateTime')}")
    else:
        print("\n❌ Failed to get order status. Check logs for details.")

def handle_cancel_order(args, logger):
    """Handle order cancellation."""
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    market_manager = MarketOrderManager(api_key, api_secret, testnet=True)
    
    print(f"\nCancelling order...")
    print(f"Symbol: {args.symbol}")
    print(f"Order ID: {args.order_id}")
    
    result = market_manager.cancel_order(args.symbol, args.order_id)
    
    if result:
        print("\n✅ Order Cancelled Successfully!")
        print(f"Order ID: {result.get('orderId')}")
        print(f"Symbol: {result.get('symbol')}")
        print(f"Status: {result.get('status')}")
    else:
        print("\n❌ Failed to cancel order. Check logs for details.")

def handle_oco_order(args, logger):
    """Handle OCO order placement."""
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    oco_manager = OCOOrderManager(api_key, api_secret, testnet=True)
    
    print(f"\nPlacing OCO {args.side.upper()} Order...")
    print(f"Symbol: {args.symbol}")
    print(f"Quantity: {args.quantity}")
    print(f"Take Profit Price: {args.take_profit_price}")
    print(f"Stop Loss Price: {args.stop_loss_price}")
    
    result = oco_manager.place_oco_order(
        symbol=args.symbol,
        side=args.side,
        quantity=args.quantity,
        take_profit_price=args.take_profit_price,
        stop_loss_price=args.stop_loss_price,
        time_in_force=args.time_in_force
    )
    
    if result:
        tp_order, sl_order = result
        print("\n✅ OCO Order Placed Successfully!")
        print(f"Take Profit Order ID: {tp_order.get('orderId')}")
        print(f"Stop Loss Order ID: {sl_order.get('orderId')}")
        print(f"Symbol: {tp_order.get('symbol')}")
        print(f"Side: {tp_order.get('side')}")
        print(f"Quantity: {tp_order.get('origQty')}")
    else:
        print("\n❌ Failed to place OCO order. Check logs for details.")

def handle_twap_order(args, logger):
    """Handle TWAP order placement."""
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    twap_manager = TWAPOrderManager(api_key, api_secret, testnet=True)
    
    print(f"\nStarting TWAP {args.side.upper()} Order...")
    print(f"Symbol: {args.symbol}")
    print(f"Total Quantity: {args.total_quantity}")
    print(f"Duration: {args.duration_minutes} minutes")
    print(f"Order Type: {args.order_type}")
    if args.limit_price:
        print(f"Limit Price: {args.limit_price}")
    
    def twap_callback(twap_id, event, data):
        if event == 'CHUNK_COMPLETED':
            print(f"✅ Chunk {data['chunk_number']} completed: {data['chunk_quantity']} {args.symbol}")
            print(f"Total executed: {data['total_executed']}")
        elif event == 'COMPLETED':
            print(f"\n🏁 TWAP order completed!")
            print(f"Total executed: {data['total_executed']}")
            print(f"TWAP price: {data.get('twap_price', 'N/A')}")
        elif event == 'PRICE_DEVIATION':
            print(f"⚠️  Price deviation warning: {data['deviation']:.2%}")
    
    twap_id = twap_manager.place_twap_order(
        symbol=args.symbol,
        side=args.side,
        total_quantity=args.total_quantity,
        duration_minutes=args.duration_minutes,
        num_orders=args.num_orders,
        order_type=args.order_type,
        limit_price=args.limit_price,
        callback=twap_callback
    )
    
    if twap_id:
        print(f"\n✅ TWAP Order Started Successfully!")
        print(f"TWAP ID: {twap_id}")
        print("Monitor the progress above. The order will execute in background.")
        print("Use Ctrl+C to stop monitoring (TWAP will continue running)")
        
        # Keep monitoring until user stops or TWAP completes
        try:
            while True:
                status = twap_manager.get_twap_status(twap_id)
                if status and status['status'] != 'ACTIVE':
                    break
                time.sleep(2)
        except KeyboardInterrupt:
            print("\n⏸️  Monitoring stopped. TWAP continues in background.")
            print(f"Use the status command to check TWAP progress later.")
    else:
        print("\n❌ Failed to start TWAP order. Check logs for details.")

def handle_grid_order(args, logger):
    """Handle grid order setup."""
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    grid_manager = GridOrderManager(api_key, api_secret, testnet=True)
    
    print(f"\nStarting Grid Trading...")
    print(f"Symbol: {args.symbol}")
    if args.center_price:
        print(f"Center Price: {args.center_price}")
    else:
        print("Center Price: Current market price")
    print(f"Price Range: {args.price_range_percent:.1%}")
    print(f"Grid Levels: {args.grid_count}")
    
    if args.order_quantity:
        print(f"Quantity per Order: {args.order_quantity}")
    elif args.total_investment:
        print(f"Total Investment: {args.total_investment}")
    else:
        print("❌ Error: Either --order-quantity or --total-investment must be specified")
        return
    
    def grid_callback(grid_id, event, data):
        if event == 'UPDATE':
            print(f"📊 Grid Update - Buy Orders: {data['active_buy_orders']}, "
                  f"Sell Orders: {data['active_sell_orders']}, "
                  f"Profit: {data['total_profit']:.4f}")
    
    grid_id = grid_manager.place_grid_orders(
        symbol=args.symbol,
        center_price=args.center_price,
        price_range_percent=args.price_range_percent,
        grid_count=args.grid_count,
        order_quantity=args.order_quantity,
        total_investment=args.total_investment,
        callback=grid_callback
    )
    
    if grid_id:
        print(f"\n✅ Grid Trading Started Successfully!")
        print(f"Grid ID: {grid_id}")
        print("Monitor the grid progress above. Trading will continue in background.")
        print("Use Ctrl+C to stop monitoring (grid will continue running)")
        
        # Keep monitoring until user stops
        try:
            while True:
                status = grid_manager.get_grid_status(grid_id)
                if status and status['status'] != 'ACTIVE':
                    break
                time.sleep(10)  # Update every 10 seconds
        except KeyboardInterrupt:
            print("\n⏸️  Monitoring stopped. Grid continues in background.")
            print(f"Grid ID {grid_id} is still active.")
    else:
        print("\n❌ Failed to start grid trading. Check logs for details.")

def main():
    """Main CLI interface."""
    logger = setup_logging()
    logger.info("Starting Binance Trading Bot CLI")
    
    parser = argparse.ArgumentParser(description='Binance USDT-M Futures Trading Bot')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Market order command
    market_parser = subparsers.add_parser('market', help='Place market order')
    market_parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    market_parser.add_argument('side', choices=['buy', 'sell'], help='Order side')
    market_parser.add_argument('quantity', type=float, help='Order quantity')
    market_parser.add_argument('--reduce-only', action='store_true', 
                              help='Reduce only order')
    
    # Limit order command
    limit_parser = subparsers.add_parser('limit', help='Place limit order')
    limit_parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    limit_parser.add_argument('side', choices=['buy', 'sell'], help='Order side')
    limit_parser.add_argument('quantity', type=float, help='Order quantity')
    limit_parser.add_argument('price', type=float, help='Order price')
    limit_parser.add_argument('--time-in-force', choices=['GTC', 'IOC', 'FOK'], 
                             default='GTC', help='Time in force')
    limit_parser.add_argument('--reduce-only', action='store_true', 
                             help='Reduce only order')
    
    # Order status command
    status_parser = subparsers.add_parser('status', help='Check order status')
    status_parser.add_argument('symbol', help='Trading symbol')
    status_parser.add_argument('order_id', type=int, help='Order ID')
    
    # Cancel order command
    cancel_parser = subparsers.add_parser('cancel', help='Cancel order')
    cancel_parser.add_argument('symbol', help='Trading symbol')
    cancel_parser.add_argument('order_id', type=int, help='Order ID')
    
    # OCO order command
    oco_parser = subparsers.add_parser('oco', help='Place OCO (One-Cancels-Other) order')
    oco_parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    oco_parser.add_argument('side', choices=['buy', 'sell'], help='Order side')
    oco_parser.add_argument('quantity', type=float, help='Order quantity')
    oco_parser.add_argument('take_profit_price', type=float, help='Take profit price')
    oco_parser.add_argument('stop_loss_price', type=float, help='Stop loss price')
    oco_parser.add_argument('--time-in-force', choices=['GTC', 'IOC', 'FOK'], 
                           default='GTC', help='Time in force')
    
    # TWAP order command
    twap_parser = subparsers.add_parser('twap', help='Place TWAP (Time-Weighted Average Price) order')
    twap_parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    twap_parser.add_argument('side', choices=['buy', 'sell'], help='Order side')
    twap_parser.add_argument('total_quantity', type=float, help='Total quantity to execute')
    twap_parser.add_argument('duration_minutes', type=int, help='Duration in minutes')
    twap_parser.add_argument('--num-orders', type=int, help='Number of orders to split into')
    twap_parser.add_argument('--order-type', choices=['MARKET', 'LIMIT'], 
                            default='MARKET', help='Order type')
    twap_parser.add_argument('--limit-price', type=float, help='Limit price (for limit orders)')
    
    # Grid order command
    grid_parser = subparsers.add_parser('grid', help='Start grid trading')
    grid_parser.add_argument('symbol', help='Trading symbol (e.g., BTCUSDT)')
    grid_parser.add_argument('--center-price', type=float, help='Center price (current price if not set)')
    grid_parser.add_argument('--price-range-percent', type=float, default=0.05, 
                            help='Price range as percentage (default: 0.05 = 5%%)')
    grid_parser.add_argument('--grid-count', type=int, default=10, 
                            help='Number of grid levels (default: 10)')
    grid_parser.add_argument('--order-quantity', type=float, help='Quantity per order')
    grid_parser.add_argument('--total-investment', type=float, 
                            help='Total investment amount (auto-calc quantity)')
    
    # Help command
    help_parser = subparsers.add_parser('help', help='Show detailed help')
    
    args = parser.parse_args()
    
    if not args.command or args.command == 'help':
        print_help()
        return
    
    try:
        if args.command == 'market':
            handle_market_order(args, logger)
        elif args.command == 'limit':
            handle_limit_order(args, logger)
        elif args.command == 'status':
            handle_order_status(args, logger)
        elif args.command == 'cancel':
            handle_cancel_order(args, logger)
        elif args.command == 'oco':
            handle_oco_order(args, logger)
        elif args.command == 'twap':
            handle_twap_order(args, logger)
        elif args.command == 'grid':
            handle_grid_order(args, logger)
    except KeyboardInterrupt:
        print("\n\nBot interrupted by user")
        logger.info("Bot interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        logger.error(f"Unexpected error: {e}")

def print_help():
    """Print detailed help information."""
    print("""
🚀 Binance USDT-M Futures Trading Bot

SETUP:
1. Set your API credentials:
   export BINANCE_API_KEY='your_testnet_api_key'
   export BINANCE_API_SECRET='your_testnet_api_secret'

2. Bot uses Binance Futures Testnet by default

USAGE EXAMPLES:

📈 Market Orders:
   python main.py market BTCUSDT buy 0.001
   python main.py market ETHUSDT sell 0.01 --reduce-only

📊 Limit Orders:
   python main.py limit BTCUSDT buy 0.001 45000
   python main.py limit ETHUSDT sell 0.01 3500 --time-in-force IOC

🔍 Check Order Status:
   python main.py status BTCUSDT 123456789

❌ Cancel Order:
   python main.py cancel BTCUSDT 123456789

🔄 Advanced Orders:
   python main.py oco BTCUSDT buy 0.001 50000 45000
   python main.py twap ETHUSDT sell 0.1 30 --order-type MARKET
   python main.py grid BTCUSDT --total-investment 1000 --grid-count 20

📝 All orders are logged to bot.log file

⚠️  IMPORTANT:
- This bot uses Binance Futures Testnet
- Never use real funds without thorough testing
- Always validate symbols and quantities before trading
- OCO, TWAP, and Grid orders run in background - use Ctrl+C to stop monitoring
    """)

if __name__ == '__main__':
    main()