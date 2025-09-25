"""
Binance USDT-M Futures Trading Bot
Interactive CLI-based trading bot with support for multiple order types.
"""

import os
import sys
import logging
from typing import Optional
from dotenv import load_dotenv
import colorama
from colorama import Fore, Style

load_dotenv()
colorama.init()

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
    """Get API credentials from .env file."""
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        print("Error: Set BINANCE_API_KEY and BINANCE_API_SECRET in .env")
        return None, None
    
    return api_key, api_secret

def print_banner():
    """Print the trading bot banner."""
    print(Fore.GREEN + Style.BRIGHT + """
╔══════════════════════════════════════════════════════════════════╗
║                    BINANCE FUTURES TRADING BOT                  ║
║                      Interactive CLI Interface                  ║
╚══════════════════════════════════════════════════════════════════╝
""" + Style.RESET_ALL)

def print_menu():
    """Print the main menu."""
    print(Fore.GREEN + "\n" + "="*70)
    print(Fore.GREEN + Style.BRIGHT + "                          TRADING MENU")
    print(Fore.GREEN + "="*70)
    print(Fore.WHITE + """
1.  Market Order          - Execute immediately at market price
2.  Limit Order           - Execute at specific price or better  
3.  OCO Order             - One-Cancels-Other order strategy
4.  TWAP Order            - Time-Weighted Average Price execution
5.  Grid Trading          - Automated grid trading strategy
6.  Check Order Status    - View all orders for a symbol
7.  Cancel Order          - Cancel pending order
8.  Check Balance         - View account balance and positions
9.  Help                 - Show detailed help information
10. Exit                  - Close the application
""")
    print(Fore.GREEN + "="*70 + Style.RESET_ALL)

def get_user_input(prompt: str, input_type: str = "str", required: bool = True):
    """Get user input with validation."""
    while True:
        try:
            user_input = input(Fore.CYAN + f"➤ {prompt}: " + Fore.WHITE).strip()
            
            if not user_input and required:
                print(Fore.RED + "This field is required. Please enter a value." + Style.RESET_ALL)
                continue
            
            if not user_input and not required:
                return None
                
            if input_type == "float":
                return float(user_input)
            elif input_type == "int":
                return int(user_input)
            else:
                return user_input
                
        except ValueError:
            print(Fore.RED + f"Invalid {input_type}. Please try again." + Style.RESET_ALL)
        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n⚠️  Operation cancelled by user." + Style.RESET_ALL)
            return None

def print_order_result(result: Optional[dict], order_type: str):
    """Print formatted order result with detailed information."""
    if result:
        print(Fore.GREEN + "\n" + "="*70)
        print(Fore.GREEN + Style.BRIGHT + f"          {order_type.upper()} ORDER SUCCESSFUL")
        print(Fore.GREEN + "="*70)
        print(Fore.WHITE + f"📊 Order Details:")
        print(f"   🆔 Order ID: {Fore.CYAN}{result.get('orderId')}{Fore.WHITE}")
        print(f"   📈 Symbol: {Fore.CYAN}{result.get('symbol')}{Fore.WHITE}")
        print(f"   📍 Side: {Fore.CYAN}{result.get('side')}{Fore.WHITE}")
        print(f"   📊 Status: {Fore.GREEN if result.get('status') in ['NEW', 'FILLED'] else Fore.YELLOW}{result.get('status')}{Fore.WHITE}")
        print(f"   📦 Quantity: {Fore.CYAN}{result.get('origQty')}{Fore.WHITE}")
        print(f"   💰 Executed: {Fore.CYAN}{result.get('executedQty', '0')}{Fore.WHITE}")
        
        if 'price' in result and float(result.get('price', 0)) > 0:
            print(f"   💵 Price: {Fore.CYAN}{result.get('price')}{Fore.WHITE}")
        
        if 'avgPrice' in result and float(result.get('avgPrice', 0)) > 0:
            print(f"   📈 Avg Price: {Fore.CYAN}{result.get('avgPrice')}{Fore.WHITE}")
            
        if 'timeInForce' in result:
            print(f"   ⏰ Time in Force: {Fore.CYAN}{result.get('timeInForce')}{Fore.WHITE}")
            
        print(f"   🕐 Update Time: {Fore.CYAN}{result.get('updateTime', 'N/A')}{Fore.WHITE}")
        print(Fore.GREEN + "="*70 + Style.RESET_ALL)
        
        # Show quick action hint
        if result.get('status') == 'NEW':
            print(Fore.YELLOW + f"💡 Order is pending. Use option 6 to check status with Order ID: {result.get('orderId')}" + Style.RESET_ALL)
        elif result.get('status') == 'FILLED':
            print(Fore.GREEN + "🎉 Order completed successfully!" + Style.RESET_ALL)
    else:
        print(Fore.RED + "\n" + "="*70)
        print(Fore.RED + Style.BRIGHT + f"          ❌ {order_type.upper()} ORDER FAILED")
        print(Fore.RED + "="*70)
        print(Fore.WHITE + "📋 Common issues and solutions:")
        print(Fore.WHITE + "   • Insufficient margin - Try smaller quantity")
        print(Fore.WHITE + "   • Invalid price/quantity - Check symbol requirements")
        print(Fore.WHITE + "   • Position limits - Close existing positions first")
        print(Fore.WHITE + "   • Network issues - Try again in a moment")
        print(Fore.WHITE + "💡 Check logs above for specific error details")
        print(Fore.RED + "="*70 + Style.RESET_ALL)

def print_success(message: str):
    """Print success message."""
    print(Fore.GREEN + f"{message}" + Style.RESET_ALL)

def print_error(message: str):
    """Print error message."""
    print(Fore.RED + f"❌ {message}" + Style.RESET_ALL)

def print_info(message: str):
    """Print info message."""
    print(Fore.CYAN + f"ℹ️  {message}" + Style.RESET_ALL)

def handle_market_order_interactive(logger):
    """Interactive market order placement."""
    print(Fore.YELLOW + "\n📈 MARKET ORDER" + Style.RESET_ALL)
    print("Execute immediately at current market price\n")
    
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    symbol = get_user_input("Trading Symbol (e.g., BTCUSDT)").upper()
    side = get_user_input("Order Side (buy/sell)").lower()
    if side not in ['buy', 'sell']:
        print_error("Invalid side. Must be 'buy' or 'sell'")
        return
    
    quantity = get_user_input("Quantity", "float")
    reduce_only = get_user_input("Reduce Only? (y/n)", required=False) in ['y', 'yes']
    
    if not confirm_action(f"Place {side.upper()} market order for {quantity} {symbol}?"):
        print_info("Order cancelled")
        return
    
    market_manager = MarketOrderManager(api_key, api_secret, testnet=True)
    result = market_manager.place_market_order(symbol, side, quantity, reduce_only)
    print_order_result(result, "Market")
    
    # Suggest balance check if order failed
    if not result:
        print(Fore.YELLOW + f"💡 Tip: Use option 8 to check your account balance and get trading suggestions" + Style.RESET_ALL)

def handle_limit_order_interactive(logger):
    """Interactive limit order placement."""
    print(Fore.YELLOW + "\n📊 LIMIT ORDER" + Style.RESET_ALL)
    print("Execute at specific price or better\n")
    
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    symbol = get_user_input("Trading Symbol (e.g., BTCUSDT)").upper()
    side = get_user_input("Order Side (buy/sell)").lower()
    if side not in ['buy', 'sell']:
        print_error("Invalid side. Must be 'buy' or 'sell'")
        return
    
    quantity = get_user_input("Quantity", "float")
    price = get_user_input("Price", "float")
    
    print("\nTime in Force options:")
    print("  GTC - Good Till Cancelled")
    print("  IOC - Immediate or Cancel")
    print("  FOK - Fill or Kill")
    time_in_force = get_user_input("Time in Force (GTC/IOC/FOK)", required=False) or "GTC"
    time_in_force = time_in_force.upper()
    
    if time_in_force not in ['GTC', 'IOC', 'FOK']:
        print_error("Invalid time in force")
        return
    
    reduce_only = get_user_input("Reduce Only? (y/n)", required=False) in ['y', 'yes']
    
    if not confirm_action(f"Place {side.upper()} limit order for {quantity} {symbol} at {price}?"):
        print_info("Order cancelled")
        return
    
    limit_manager = LimitOrderManager(api_key, api_secret, testnet=True)
    result = limit_manager.place_limit_order(symbol, side, quantity, price, time_in_force, reduce_only)
    print_order_result(result, "Limit")

def confirm_action(message: str) -> bool:
    """Ask for user confirmation."""
    while True:
        response = input(Fore.YELLOW + f"⚠️  {message} (y/n): " + Fore.WHITE).strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        print(Fore.RED + "❌ Please enter 'y' or 'n'" + Style.RESET_ALL)

def handle_oco_order_interactive(logger):
    """Interactive OCO order placement."""
    print(Fore.YELLOW + "\n🎯 OCO ORDER" + Style.RESET_ALL)
    print("One-Cancels-Other order strategy\n")
    
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    symbol = get_user_input("Trading Symbol (e.g., BTCUSDT)").upper()
    side = get_user_input("Order Side (buy/sell)").lower()
    if side not in ['buy', 'sell']:
        print_error("Invalid side. Must be 'buy' or 'sell'")
        return
    
    quantity = get_user_input("Quantity", "float")
    take_profit_price = get_user_input("Take Profit Price", "float")
    stop_loss_price = get_user_input("Stop Loss Price", "float")
    
    time_in_force = get_user_input("Time in Force (GTC/IOC/FOK)", required=False) or "GTC"
    time_in_force = time_in_force.upper()
    
    if not confirm_action(f"Place OCO {side.upper()} order for {quantity} {symbol}?"):
        print_info("Order cancelled")
        return
    
    oco_manager = OCOOrderManager(api_key, api_secret, testnet=True)
    result = oco_manager.place_oco_order(symbol, side, quantity, take_profit_price, stop_loss_price, time_in_force)
    
    if result:
        tp_order, sl_order = result
        print(Fore.GREEN + "\n" + "="*70)
        print(Fore.GREEN + Style.BRIGHT + "              ✅ OCO ORDER SUCCESSFUL")
        print(Fore.GREEN + "="*70)
        print(Fore.WHITE + f"🎯 OCO Order Details:")
        print(f"   📈 Symbol: {Fore.CYAN}{tp_order.get('symbol')}{Fore.WHITE}")
        print(f"   📍 Side: {Fore.CYAN}{tp_order.get('side')}{Fore.WHITE}")
        print(f"   📦 Quantity: {Fore.CYAN}{tp_order.get('origQty')}{Fore.WHITE}")
        print(f"\n   💰 Take Profit Order:")
        print(f"      🆔 Order ID: {Fore.CYAN}{tp_order.get('orderId')}{Fore.WHITE}")
        print(f"      💵 Price: {Fore.CYAN}{take_profit_price}{Fore.WHITE}")
        print(f"      📊 Status: {Fore.GREEN}{tp_order.get('status')}{Fore.WHITE}")
        print(f"\n   🛑 Stop Loss Order:")
        print(f"      🆔 Order ID: {Fore.CYAN}{sl_order.get('orderId')}{Fore.WHITE}")
        print(f"      💵 Price: {Fore.CYAN}{stop_loss_price}{Fore.WHITE}")
        print(f"      📊 Status: {Fore.GREEN}{sl_order.get('status')}{Fore.WHITE}")
        print(Fore.GREEN + "="*70 + Style.RESET_ALL)
        print(Fore.GREEN + "🎉 OCO orders placed successfully! One will cancel the other when executed." + Style.RESET_ALL)
    else:
        print(Fore.RED + "\n" + "="*70)
        print(Fore.RED + Style.BRIGHT + "              ❌ OCO ORDER FAILED")
        print(Fore.RED + "="*70)
        print(Fore.WHITE + "📋 Please check the logs for more details")
        print(Fore.RED + "="*70 + Style.RESET_ALL)

def handle_twap_order_interactive(logger):
    """Interactive TWAP order placement."""
    print(Fore.YELLOW + "\n⏱️ TWAP ORDER" + Style.RESET_ALL)
    print("Time-Weighted Average Price - Split large orders into smaller chunks over time\n")
    
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    twap_manager = TWAPOrderManager(api_key, api_secret, testnet=True)
    
    # Get order details
    symbol = get_user_input("Trading Symbol").upper()
    
    # Validate symbol
    if not twap_manager.validate_symbol(symbol):
        print(Fore.RED + f"❌ Invalid symbol: {symbol}" + Style.RESET_ALL)
        return
    
    side = get_user_input("Side (BUY/SELL)").upper()
    if side not in ['BUY', 'SELL']:
        print(Fore.RED + "❌ Invalid side. Must be BUY or SELL" + Style.RESET_ALL)
        return
    
    try:
        total_quantity = float(get_user_input("Total Quantity"))
        duration_minutes = int(get_user_input("Duration (minutes)"))
        chunks = int(get_user_input("Number of chunks"))
        
        if total_quantity <= 0 or duration_minutes <= 0 or chunks <= 0:
            print(Fore.RED + "❌ All values must be positive" + Style.RESET_ALL)
            return
            
    except ValueError:
        print(Fore.RED + "❌ Invalid numeric input" + Style.RESET_ALL)
        return
    
    print(Fore.CYAN + f"\n🔄 Starting TWAP order for {total_quantity} {symbol}..." + Style.RESET_ALL)
    print(f"📊 Will execute {chunks} orders over {duration_minutes} minutes")
    
    # Execute TWAP order
    twap_id = twap_manager.place_twap_order(
        symbol=symbol,
        side=side,
        total_quantity=total_quantity,
        duration_minutes=duration_minutes,
        num_orders=chunks
    )
    
    if twap_id:
        print(Fore.GREEN + "\n" + "="*70)
        print(Fore.GREEN + Style.BRIGHT + "              ✅ TWAP ORDER STARTED")
        print(Fore.GREEN + "="*70)
        print(Fore.WHITE + f"📈 Symbol: {Fore.CYAN}{symbol}{Fore.WHITE}")
        print(Fore.WHITE + f"📊 Side: {Fore.CYAN}{side}{Fore.WHITE}")
        print(Fore.WHITE + f"💰 Total Quantity: {Fore.CYAN}{total_quantity}{Fore.WHITE}")
        print(Fore.WHITE + f"⏱️ Duration: {Fore.CYAN}{duration_minutes} minutes{Fore.WHITE}")
        print(Fore.WHITE + f"🔢 Chunks: {Fore.CYAN}{chunks}{Fore.WHITE}")
        print(Fore.WHITE + f"🆔 TWAP ID: {Fore.CYAN}{twap_id}{Fore.WHITE}")
        print(Fore.GREEN + "="*70 + Style.RESET_ALL)
        print(Fore.GREEN + "🎉 TWAP order is now running in the background!" + Style.RESET_ALL)
    else:
        print(Fore.RED + "\n" + "="*70)
        print(Fore.RED + Style.BRIGHT + "              ❌ TWAP ORDER FAILED")
        print(Fore.RED + "="*70)
        print(Fore.WHITE + "📋 Please check the logs for more details")
        print(Fore.RED + "="*70 + Style.RESET_ALL)

def handle_grid_trading_interactive(logger):
    """Interactive Grid trading setup."""
    print(Fore.YELLOW + "\n🔲 GRID TRADING" + Style.RESET_ALL)
    print("Automated grid trading strategy - Buy low, sell high within price ranges\n")
    
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    grid_manager = GridOrderManager(api_key, api_secret, testnet=True)
    
    # Get grid parameters
    symbol = get_user_input("Trading Symbol").upper()
    
    # Validate symbol
    if not grid_manager.validate_symbol(symbol):
        print(Fore.RED + f"❌ Invalid symbol: {symbol}" + Style.RESET_ALL)
        return
    
    try:
        lower_price = float(get_user_input("Lower Price Range"))
        upper_price = float(get_user_input("Upper Price Range"))
        grid_levels = int(get_user_input("Number of Grid Levels"))
        quantity_per_level = float(get_user_input("Quantity per Level"))
        
        if lower_price >= upper_price:
            print(Fore.RED + "❌ Lower price must be less than upper price" + Style.RESET_ALL)
            return
            
        if grid_levels <= 0 or quantity_per_level <= 0:
            print(Fore.RED + "❌ Grid levels and quantity must be positive" + Style.RESET_ALL)
            return
        
        # Calculate center price and range percentage
        center_price = (lower_price + upper_price) / 2
        price_range_percent = (upper_price - lower_price) / center_price
            
    except ValueError:
        print(Fore.RED + "❌ Invalid numeric input" + Style.RESET_ALL)
        return
    
    print(Fore.CYAN + f"\n🔄 Setting up Grid Trading for {symbol}..." + Style.RESET_ALL)
    print(f"📊 Price Range: {lower_price} - {upper_price}")
    print(f"🎯 Center Price: {center_price}")
    print(f"🔢 Grid Levels: {grid_levels}")
    print(f"💰 Quantity per Level: {quantity_per_level}")
    
    # Start grid trading
    grid_id = grid_manager.place_grid_orders(
        symbol=symbol,
        center_price=center_price,
        price_range_percent=price_range_percent,
        grid_count=grid_levels,
        order_quantity=quantity_per_level
    )
    
    if grid_id:
        print(Fore.GREEN + "\n" + "="*70)
        print(Fore.GREEN + Style.BRIGHT + "              ✅ GRID TRADING STARTED")
        print(Fore.GREEN + "="*70)
        print(Fore.WHITE + f"📈 Symbol: {Fore.CYAN}{symbol}{Fore.WHITE}")
        print(Fore.WHITE + f"💹 Price Range: {Fore.CYAN}{lower_price} - {upper_price}{Fore.WHITE}")
        print(Fore.WHITE + f"🎯 Center Price: {Fore.CYAN}{center_price:.4f}{Fore.WHITE}")
        print(Fore.WHITE + f"🔢 Grid Levels: {Fore.CYAN}{grid_levels}{Fore.WHITE}")
        print(Fore.WHITE + f"💰 Quantity/Level: {Fore.CYAN}{quantity_per_level}{Fore.WHITE}")
        print(Fore.WHITE + f"🆔 Grid ID: {Fore.CYAN}{grid_id}{Fore.WHITE}")
        print(Fore.GREEN + "="*70 + Style.RESET_ALL)
        print(Fore.GREEN + "🎉 Grid trading is now active! Orders will be placed automatically." + Style.RESET_ALL)
    else:
        print(Fore.RED + "\n" + "="*70)
        print(Fore.RED + Style.BRIGHT + "              ❌ GRID TRADING FAILED")
        print(Fore.RED + "="*70)
        print(Fore.WHITE + "📋 Please check the logs for more details")
        print(Fore.RED + "="*70 + Style.RESET_ALL)

def handle_order_status_interactive(logger):
    """Interactive order status check for all orders of a symbol."""
    print(Fore.YELLOW + "\n📋 CHECK ORDER STATUS" + Style.RESET_ALL)
    print("View all orders for a trading symbol\n")
    
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    symbol = get_user_input("Trading Symbol").upper()
    
    print(Fore.CYAN + f"\n🔍 Fetching all orders for {symbol}..." + Style.RESET_ALL)
    
    market_manager = MarketOrderManager(api_key, api_secret, testnet=True)
    
    try:
        # Get all orders for the symbol
        from binance.client import Client
        client = Client(api_key, api_secret, testnet=True)
        client.API_URL = 'https://testnet.binancefuture.com'
        
        all_orders = client.futures_get_all_orders(symbol=symbol, limit=20)  # Get last 20 orders
        
        if not all_orders:
            print(Fore.YELLOW + f"\n📋 No orders found for {symbol}" + Style.RESET_ALL)
            return
        
        print(Fore.GREEN + "\n" + "="*80)
        print(Fore.GREEN + Style.BRIGHT + f"               📋 ALL ORDERS FOR {symbol}")
        print(Fore.GREEN + "="*80)
        
        # Group orders by status
        active_orders = []
        filled_orders = []
        cancelled_orders = []
        
        for order in all_orders:
            if order['status'] in ['NEW', 'PARTIALLY_FILLED']:
                active_orders.append(order)
            elif order['status'] == 'FILLED':
                filled_orders.append(order)
            else:
                cancelled_orders.append(order)
        
        # Show active orders first
        if active_orders:
            print(Fore.YELLOW + Style.BRIGHT + f"\n🔄 ACTIVE ORDERS ({len(active_orders)}):")
            print(Fore.GREEN + "-" * 80)
            for order in active_orders:
                display_order_summary(order, is_active=True)
        
        # Show recent filled orders
        if filled_orders:
            print(Fore.GREEN + Style.BRIGHT + f"\n✅ FILLED ORDERS ({len(filled_orders)} - showing last 10):")
            print(Fore.GREEN + "-" * 80)
            for order in filled_orders[-10:]:  # Show last 10 filled orders
                display_order_summary(order, is_active=False)
        
        # Show cancelled orders if any
        if cancelled_orders:
            print(Fore.RED + Style.BRIGHT + f"\n❌ CANCELLED ORDERS ({len(cancelled_orders)} - showing last 5):")
            print(Fore.GREEN + "-" * 80)
            for order in cancelled_orders[-5:]:  # Show last 5 cancelled orders
                display_order_summary(order, is_active=False)
        
        print(Fore.GREEN + "="*80 + Style.RESET_ALL)
        
        # Show summary statistics
        total_orders = len(all_orders)
        total_filled = len(filled_orders)
        success_rate = (total_filled / total_orders * 100) if total_orders > 0 else 0
        
        print(Fore.CYAN + f"📊 Summary: {total_orders} total orders, {len(active_orders)} active, {total_filled} filled ({success_rate:.1f}% success rate)" + Style.RESET_ALL)
        
        if active_orders:
            print(Fore.YELLOW + f"� You have {len(active_orders)} active orders. Use option 7 to cancel if needed." + Style.RESET_ALL)
            
    except Exception as e:
        print(Fore.RED + f"\n❌ Error fetching orders for {symbol}: {e}" + Style.RESET_ALL)
        logger.error(f"Error fetching orders for {symbol}: {e}")

def display_order_summary(order, is_active=False):
    """Display a single order summary in a compact format."""
    order_id = order.get('orderId')
    side = order.get('side')
    order_type = order.get('type')
    quantity = order.get('origQty')
    executed_qty = order.get('executedQty', '0')
    status = order.get('status')
    
    # Color coding
    side_color = Fore.GREEN if side == 'BUY' else Fore.RED
    status_color = Fore.GREEN if status == 'FILLED' else Fore.YELLOW if status in ['NEW', 'PARTIALLY_FILLED'] else Fore.RED
    
    # Format price
    price_info = ""
    if order.get('price') and float(order.get('price', 0)) > 0:
        price_info = f" @ ${order.get('price')}"
    elif order.get('avgPrice') and float(order.get('avgPrice', 0)) > 0:
        price_info = f" @ ${order.get('avgPrice')} (avg)"
    
    # Progress for partial fills
    progress_info = ""
    if float(quantity) > 0:
        exec_percent = (float(executed_qty) / float(quantity)) * 100
        if exec_percent > 0 and exec_percent < 100:
            progress_info = f" ({exec_percent:.1f}% filled)"
    
    # Time info
    import datetime
    update_time = datetime.datetime.fromtimestamp(order.get('updateTime', 0) / 1000)
    time_str = update_time.strftime("%m/%d %H:%M")
    
    print(f"   🆔 {Fore.CYAN}{order_id}{Fore.WHITE} | {side_color}{side}{Fore.WHITE} {order_type} | "
          f"📦 {quantity}{progress_info} | {status_color}{status}{Fore.WHITE}{price_info} | � {time_str}")
    
    if is_active and status == 'NEW':
        print(f"      💡 {Fore.YELLOW}Can be cancelled with option 7{Fore.WHITE}")

def handle_cancel_order_interactive(logger):
    """Interactive order cancellation."""
    print(Fore.YELLOW + "\n❌ CANCEL ORDER" + Style.RESET_ALL)
    print("Cancel a pending order\n")
    
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    symbol = get_user_input("Trading Symbol").upper()
    order_id = get_user_input("Order ID", "int")
    
    if not confirm_action(f"Cancel order {order_id} for {symbol}?"):
        print_info("Cancellation cancelled")
        return
    
    print(Fore.CYAN + f"\n🚫 Cancelling order: {symbol} #{order_id}" + Style.RESET_ALL)
    
    market_manager = MarketOrderManager(api_key, api_secret, testnet=True)
    result = market_manager.cancel_order(symbol, order_id)
    
    if result:
        print(Fore.GREEN + "\n" + "="*70)
        print(Fore.GREEN + Style.BRIGHT + "              ✅ ORDER CANCELLED SUCCESSFULLY")
        print(Fore.GREEN + "="*70)
        print(Fore.WHITE + f"📊 Cancellation Details:")
        print(f"   🆔 Order ID: {Fore.CYAN}{result.get('orderId')}{Fore.WHITE}")
        print(f"   📈 Symbol: {Fore.CYAN}{result.get('symbol')}{Fore.WHITE}")
        print(f"   📊 Status: {Fore.RED}{result.get('status')}{Fore.WHITE}")
        if 'clientOrderId' in result:
            print(f"   🏷️  Client Order ID: {Fore.CYAN}{result.get('clientOrderId')}{Fore.WHITE}")
        print(Fore.GREEN + "="*70 + Style.RESET_ALL)
        print(Fore.GREEN + "🎉 Order has been successfully cancelled!" + Style.RESET_ALL)
    else:
        print(Fore.RED + "\n" + "="*70)
        print(Fore.RED + Style.BRIGHT + "              ❌ CANCELLATION FAILED")
        print(Fore.RED + "="*70)
        print(Fore.WHITE + f"📋 Could not cancel order {order_id} for {symbol}")
        print(Fore.WHITE + "💡 Order may already be filled, cancelled, or doesn't exist")
        print(Fore.RED + "="*70 + Style.RESET_ALL)

def show_help():
    """Show detailed help information."""
    print(Fore.CYAN + """
📚 HELP INFORMATION

🔧 SETUP:
   Create a .env file with:
   BINANCE_API_KEY=your_testnet_api_key
   BINANCE_API_SECRET=your_testnet_api_secret

📈 ORDER TYPES:
   • Market Order: Executes immediately at current market price
   • Limit Order: Executes only at specified price or better
   • OCO Order: One-Cancels-Other strategy with take profit and stop loss
   • TWAP Order: Time-Weighted Average Price execution over time
   • Grid Trading: Automated buy/sell orders in a price range

⚠️  IMPORTANT:
   • This bot uses Binance Futures TESTNET
   • All trades are simulated - no real money involved
   • Always validate symbols and quantities before trading
   
📝 All trades are logged to bot.log file
""" + Style.RESET_ALL)

def handle_balance_check_interactive(logger):
    """Interactive balance and position check."""
    print(Fore.YELLOW + "\n💰 ACCOUNT BALANCE" + Style.RESET_ALL)
    print("View account balance, positions, and trading limits\n")
    
    api_key, api_secret = get_api_credentials()
    if not api_key or not api_secret:
        return
    
    from binance.client import Client
    client = Client(api_key, api_secret, testnet=True)
    client.API_URL = 'https://testnet.binancefuture.com'
    
    try:
        print(Fore.CYAN + "🔍 Fetching account information..." + Style.RESET_ALL)
        
        # Get account info
        account = client.futures_account()
        
        print(Fore.GREEN + "\n" + "="*70)
        print(Fore.GREEN + Style.BRIGHT + "               💰 ACCOUNT OVERVIEW")
        print(Fore.GREEN + "="*70)
        print(Fore.WHITE + f"💼 Account Summary:")
        print(f"   💰 Total Wallet Balance: {Fore.CYAN}{account['totalWalletBalance']} USDT{Fore.WHITE}")
        print(f"   ✅ Available Balance: {Fore.CYAN}{account['availableBalance']} USDT{Fore.WHITE}")
        print(f"   📊 Total Margin Balance: {Fore.CYAN}{account['totalMarginBalance']} USDT{Fore.WHITE}")
        
        unrealized_pnl = float(account['totalUnrealizedProfit'])
        pnl_color = Fore.GREEN if unrealized_pnl >= 0 else Fore.RED
        pnl_symbol = "+" if unrealized_pnl >= 0 else ""
        print(f"   📈 Total Unrealized PNL: {pnl_color}{pnl_symbol}{unrealized_pnl:.2f} USDT{Fore.WHITE}")
        
        print(f"\n💳 Asset Balances:")
        for balance in account['assets']:
            if float(balance['walletBalance']) > 0:
                print(f"   {balance['asset']}: {Fore.CYAN}{balance['walletBalance']}{Fore.WHITE} (Available: {Fore.CYAN}{balance['availableBalance']}{Fore.WHITE})")
        
        # Get positions
        print(f"\n📊 Open Positions:")
        positions = client.futures_position_information()
        has_positions = False
        for pos in positions:
            if float(pos['positionAmt']) != 0:
                has_positions = True
                pnl = pos.get('unRealizedProfit', pos.get('unrealizedProfit', '0'))
                pnl_val = float(pnl)
                pnl_color = Fore.GREEN if pnl_val >= 0 else Fore.RED
                pnl_symbol = "+" if pnl_val >= 0 else ""
                print(f"   📈 {pos['symbol']}: {Fore.CYAN}{pos['positionAmt']}{Fore.WHITE} (PNL: {pnl_color}{pnl_symbol}{pnl_val:.2f}{Fore.WHITE})")
        
        if not has_positions:
            print(f"   {Fore.YELLOW}No open positions{Fore.WHITE}")
        
        # Trading recommendations
        print(f"\n💡 Trading Suggestions:")
        available_balance = float(account['availableBalance'])
        
        # Get some popular symbols and their prices
        btc_ticker = client.futures_symbol_ticker(symbol='BTCUSDT')
        eth_ticker = client.futures_symbol_ticker(symbol='ETHUSDT')
        
        btc_price = float(btc_ticker['price'])
        eth_price = float(eth_ticker['price'])
        
        btc_min_order = btc_price * 0.001  # Min 0.001 BTC
        eth_min_order = eth_price * 0.01   # Min 0.01 ETH
        
        print(f"   📈 Current Prices:")
        print(f"      BTC/USDT: {Fore.CYAN}${btc_price:,.2f}{Fore.WHITE} (Min order: ${btc_min_order:.2f})")
        print(f"      ETH/USDT: {Fore.CYAN}${eth_price:,.2f}{Fore.WHITE} (Min order: ${eth_min_order:.2f})")
        
        print(f"   💰 Your available balance: {Fore.CYAN}${available_balance:.2f}{Fore.WHITE}")
        
        if available_balance >= btc_min_order:
            print(f"   ✅ {Fore.GREEN}You can trade BTC (try 0.001 BTC = ${btc_min_order:.2f}){Fore.WHITE}")
        else:
            print(f"   ❌ {Fore.RED}Insufficient funds for BTC (need ${btc_min_order:.2f}){Fore.WHITE}")
            
        if available_balance >= eth_min_order:
            print(f"   ✅ {Fore.GREEN}You can trade ETH (try 0.01 ETH = ${eth_min_order:.2f}){Fore.WHITE}")
        else:
            print(f"   ❌ {Fore.RED}Insufficient funds for ETH (need ${eth_min_order:.2f}){Fore.WHITE}")
        
        print(Fore.GREEN + "="*70 + Style.RESET_ALL)
        
        if available_balance < 100:
            print(Fore.YELLOW + "⚠️  Low balance detected! Add testnet USDT at: https://testnet.binancefuture.com/en/futures-activity/vip/gold-rush" + Style.RESET_ALL)
            
    except Exception as e:
        print(Fore.RED + f"\n❌ Error fetching account information: {e}" + Style.RESET_ALL)
        logger.error(f"Error in balance check: {e}")

def main_interactive():
    """Main interactive CLI loop."""
    logger = setup_logging()
    print_banner()
    
    while True:
        try:
            print_menu()
            choice = get_user_input("Select an option (1-10)", required=False)
            
            if choice == '1':
                handle_market_order_interactive(logger)
            elif choice == '2':
                handle_limit_order_interactive(logger)
            elif choice == '3':
                handle_oco_order_interactive(logger)
            elif choice == '4':
                handle_twap_order_interactive(logger)
            elif choice == '5':
                handle_grid_trading_interactive(logger)
            elif choice == '6':
                handle_order_status_interactive(logger)
            elif choice == '7':
                handle_cancel_order_interactive(logger)
            elif choice == '8':
                handle_balance_check_interactive(logger)
            elif choice == '9':
                show_help()
            elif choice == '10':
                print(Fore.YELLOW + "\n👋 Thank you for using Binance Trading Bot!" + Style.RESET_ALL)
                break
            else:
                print_error("Invalid option. Please select 1-10.")
                
            if choice and choice != '10':
                input(Fore.GREEN + "\nPress Enter to continue..." + Style.RESET_ALL)
                
        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n\n⚠️  Exiting... Goodbye!" + Style.RESET_ALL)
            break
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            logger.error(f"Unexpected error: {e}")



def main():
    """Main entry point"""
    main_interactive()

if __name__ == '__main__':
    main()