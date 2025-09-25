# Binance USDT-M Futures Trading Bot

A comprehensive CLI-based trading bot for Binance USDT-M Futures with support for multiple order types, robust logging, and validation.

## Features

### Core Orders

-   **Market Orders**: Instant buy/sell at current market price
-   **Limit Orders**: Buy/sell at specific price levels

### Advanced Orders

-   **Stop-Limit Orders**: Trigger limit orders when stop price is hit
-   **OCO (One-Cancels-the-Other)**: Simultaneous take-profit and stop-loss orders
-   **TWAP (Time-Weighted Average Price)**: Split large orders into smaller chunks over time
-   **Grid Orders**: Automated buy-low/sell-high within price ranges

### Key Features

-   [CHECK] Input validation (symbol, quantity, price thresholds)
-   [CHECK] Structured logging (API calls, errors, executions)
-   [CHECK] Binance Futures Testnet integration
-   [CHECK] Command-line interface
-   [CHECK] Real-time order monitoring
-   [CHECK] Error handling and recovery

## Setup

### 1. API Credentials

Get your Binance Futures Testnet API credentials:

1. Visit [Binance Futures Testnet](https://testnet.binancefuture.com/)
2. Create an account and generate API keys
3. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
# Edit .env file with your actual API keys
```

Your `.env` file should contain:

```
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```

### 2. Dependencies

Install required dependencies:

```bash
pip install -r requirements.txt
```

Required packages:

-   python-binance: Binance API client
-   requests: HTTP library
-   python-dotenv: Environment variable management

## Usage

### Market Orders

```bash
# Buy 0.001 BTC at market price
python main.py market BTCUSDT buy 0.001

# Sell 0.01 ETH at market price (reduce only)
python main.py market ETHUSDT sell 0.01 --reduce-only
```

### Limit Orders

```bash
# Buy 0.001 BTC at $45,000
python main.py limit BTCUSDT buy 0.001 45000

# Sell 0.01 ETH at $3,500 with IOC time-in-force
python main.py limit ETHUSDT sell 0.01 3500 --time-in-force IOC
```

### Order Management

```bash
# Check order status
python main.py status BTCUSDT 123456789

# Cancel order
python main.py cancel BTCUSDT 123456789
```

### Advanced Orders (Coming Soon)

The bot includes modules for advanced order types in the `src/advanced/` directory:

-   `oco.py` - OCO (One-Cancels-the-Other) orders
-   `twap.py` - TWAP (Time-Weighted Average Price) strategy
-   `grid.py` - Grid trading automation

## File Structure

```
[project_root]/
│
├── main.py                 # Main CLI interface
├── /src/                   # All source code
│   ├── market_orders.py    # Market order logic
│   ├── limit_orders.py     # Limit order logic
│   └── /advanced/          # Advanced order types
│       ├── oco.py          # OCO order logic
│       ├── twap.py         # TWAP strategy
│       └── grid.py         # Grid trading
│
├── bot.log                 # Logs (API calls, errors, executions)
└── README.md               # This file
```

## Logging

All bot activities are logged to `bot.log` with structured information:

-   API requests and responses
-   Order placement and execution
-   Errors and validation issues
-   TWAP and grid trading progress

## Safety Features

### Validation

-   Symbol existence and trading status
-   Quantity against lot size requirements
-   Price against tick size requirements
-   Order type and parameter validation

### Testnet Only

-   Bot uses Binance Futures Testnet by default
-   Safe for testing without real funds
-   All API calls go to testnet endpoints

### Error Handling

-   Comprehensive exception handling
-   Graceful degradation on API errors
-   Detailed error logging and reporting

## Important Notes

[WARNING] **Safety First**

-   This bot uses Binance Futures Testnet
-   Never use with real funds without thorough testing
-   Always validate symbols and quantities
-   Monitor logs for any issues

[INFO] **Trading Disclaimer**

-   This bot is for educational and testing purposes
-   Past performance does not guarantee future results
-   Always understand the risks before trading
-   Use proper risk management strategies

## Support

For issues or questions:

1. Check the `bot.log` file for detailed error information
2. Verify API credentials are correctly set
3. Ensure the symbol is valid and actively trading
4. Check Binance Futures Testnet status

## License

This project is for educational purposes. Use at your own risk.
