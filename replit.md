# Binance USDT-M Futures Trading Bot

## Overview

This is a comprehensive CLI-based trading bot for Binance USDT-M Futures that supports multiple order types and trading strategies. The bot provides both basic order execution (market and limit orders) and advanced trading strategies (OCO, TWAP, and Grid trading). It's designed with robust validation, structured logging, and integration with Binance's Futures Testnet for safe development and testing.

The application follows a modular architecture where each order type is implemented as a separate manager class, allowing for easy extension and maintenance. The bot emphasizes safety through extensive input validation and error handling.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Module Organization
The codebase is organized into a clear hierarchical structure:
- **Core order types** (`src/`) contain basic trading functionality (market and limit orders)
- **Advanced strategies** (`src/advanced/`) contain sophisticated trading algorithms (OCO, TWAP, Grid)
- **Main entry point** (`main.py`) provides CLI interface and orchestrates different order managers

### Trading Order Managers
Each order type is implemented as a dedicated manager class that encapsulates:
- **Binance API client initialization** with testnet support
- **Symbol and parameter validation** using exchange info
- **Order execution logic** with proper error handling
- **Structured logging** for audit trails and debugging

The managers share common validation patterns but implement order-specific logic:
- **MarketOrderManager**: Instant execution at current market prices
- **LimitOrderManager**: Price-specific order placement
- **OCOOrderManager**: Combined stop-loss and take-profit orders
- **TWAPOrderManager**: Large order splitting with time-based execution
- **GridOrderManager**: Automated range trading with multiple price levels

### CLI Interface Design
The main application uses Python's argparse for command-line argument parsing, providing a structured interface for different order types. The CLI supports environment variable configuration for API credentials, promoting security best practices.

### Error Handling Strategy
The architecture implements multi-layer error handling:
- **API-level exceptions** are caught and logged with context
- **Validation errors** prevent invalid orders from reaching the exchange
- **Order execution failures** are logged with recovery suggestions
- **Connection issues** are handled gracefully with appropriate user feedback

### Logging Architecture
Structured logging is implemented throughout the application with:
- **File-based persistence** for audit trails (`bot.log`)
- **Console output** for real-time monitoring
- **Contextual information** including timestamps, module names, and severity levels
- **API call tracking** for debugging and compliance

## External Dependencies

### Binance Exchange Integration
- **python-binance library**: Primary interface for Binance Futures API
- **Testnet environment**: Development and testing endpoint (testnet.binancefuture.com)
- **API authentication**: Key-based authentication using environment variables
- **Exchange info validation**: Real-time symbol and trading rule validation

### Python Standard Libraries
- **argparse**: Command-line interface construction
- **logging**: Structured logging and output management
- **threading**: Concurrent execution for advanced strategies (TWAP, Grid)
- **datetime**: Time-based calculations for TWAP intervals
- **decimal**: Precise numerical calculations for financial operations
- **os/sys**: Environment variable access and path management

### Development Dependencies
- **requests**: HTTP client for API communication (via python-binance)
- **json**: Data serialization for API responses and logging

The application is designed to work with minimal external dependencies, focusing on the python-binance library as the primary integration point while leveraging Python's robust standard library for core functionality.