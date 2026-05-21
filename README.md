# IQ Option API - Complete Trading Bot Framework

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![IQ Option](https://img.shields.io/badge/IQ%20Option-API-orange)](https://iqoption.com)

A complete, production-ready Python library for IQ Option automated trading. Built for the YouTube Masterclass series at [@BytecodeAutomation](https://youtube.com/@BytecodeAutomation).

**Author:** Sudip  
**YouTube:** [@BytecodeAutomation](https://youtube.com/@BytecodeAutomation)

---

## 📚 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Examples](#-examples)
  - [1. Connect & Get Balance](#1-connect--get-balance)
  - [2. Switch Account Type](#2-switch-account-type)
  - [3. Refill Demo Account](#3-refill-demo-account)
  - [4. Get Historical Candles](#4-get-historical-candles)
  - [5. Real-Time Candle Stream](#5-real-time-candle-stream)
  - [6. Get Current Price](#6-get-current-price)
  - [7. Place Binary Trade](#7-place-binary-trade)
  - [8. Place Digital Trade](#8-place-digital-trade)
  - [9. Get Position History](#9-get-position-history)
  - [10. Get Filtered Positions](#10-get-filtered-positions)
  - [11. Get Underlying Assets](#11-get-underlying-assets)
  - [12. Simple Trading Bot](#12-simple-trading-bot)
- [API Reference](#-api-reference)
- [Architecture](#-architecture)
- [YouTube Tutorial Series](#-youtube-tutorial-series)
- [Contributing](#-contributing)
- [Disclaimer](#-disclaimer)

---

## ✨ Features

### Core Features
- ✅ **Real-time candle streaming** with deque-based storage (O(1) operations)
- ✅ **Binary & Digital options trading** with full parameter validation
- ✅ **Account management** (demo/real switching, balance tracking, refill demo)
- ✅ **Position history** with pagination and time-range queries
- ✅ **Market data** (historical candles, underlying assets, CSV export)
- ✅ **WebSocket connection** with automatic message routing
- ✅ **Thread-safe callbacks** with async support (non-blocking)
- ✅ **Bidirectional asset mapping** (name ↔ ID lookups)

### Advanced Features
- 🔥 **Live candle callbacks** - Execute strategies on every new candle
- 📊 **Trade outcome checker** - Standardized P&L calculation
- 💾 **State persistence** - Save/load app state across sessions
- 🔄 **Auto-reconnection** - Robust WebSocket handling
- 📁 **CSV export** - Save candles and position history

---

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/iqoption-api.git
cd iqoption-api
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install websocket-client requests python-dotenv pandas mplfinance
```

### 3. Set Up Credentials

Create a `.env` file:

```env
IQ_EMAIL=your_email@gmail.com
IQ_PASSWORD=your_password
```

Or pass credentials directly in code:

```python
client = IQOptionClient("email@gmail.com", "password", account_type='demo')
```

---

## 🎯 Quick Start

### Basic Connection

```python
from iqoptionapi.iqapi import IQOptionClient

# Create client (demo account by default)
client = IQOptionClient("your_email@gmail.com", "your_password", account_type='demo')

# Connect to IQ Option
client.connect()

# Get account balance
balance = client.get_balance()
print(f"💰 Balance: ${balance:.2f}")

# Disconnect when done
client.disconnect()
```

### Real-Time Candle Streaming

```python
# Define callback for new candles
def on_new_candle(candle):
    print(f"🔥 New candle: {candle.asset_name}")
    print(f"   Open: {candle.open:.5f} → Close: {candle.close:.5f}")

# Register callback and start stream
client.on_new_candle(on_new_candle)
client.start_candle_stream("EURUSD", 60)

# Keep running
time.sleep(60)  # Listen for 60 seconds

# Cleanup
client.stop_candle_stream("EURUSD", 60)
```

### Place a Trade

```python
from iqoptionapi.models import OptionsTradeParams, Direction, OptionType

# Prepare trade parameters
trade = OptionsTradeParams(
    asset="EURUSD",
    expiry=1,           # 1 minute
    amount=10,          # $10
    direction=Direction.CALL,
    option_type=OptionType.BINARY_OPTION
)

# Execute trade
success, order_id = client.execute_options_trade(trade)

if success:
    print(f"✅ Trade placed! Order ID: {order_id}")
    
    # Get result after expiry
    time.sleep(65)
    success, outcome, pnl = client.get_trade_outcome(order_id, expiry=1)
    print(f"📊 Result: ${pnl:+.2f}")
else:
    print(f"❌ Trade failed: {order_id}")
```

---

## 📖 Examples

All examples are available in the `examples.py` file. Run the interactive menu:

```bash
python examples.py
```

Then choose from the menu:

```
════════════════════════════════════════════════════════════════
📚 IQ OPTION API - EXAMPLE MENU
════════════════════════════════════════════════════════════════

    1  - Connect & Get Balance
    2  - Switch Account Type
    3  - Refill Demo Account
    4  - Get Historical Candles
    5  - Real-Time Candle Stream
    6  - Get Current Price
    7  - Place Binary Trade
    8  - Place Digital Trade
    9  - Get Position History
    10 - Get Filtered Positions
    11 - Get Underlying Assets
    12 - Simple Trading Bot
    13 - Run ALL Examples
    0  - Exit
```

---

### 1. Connect & Get Balance

```python
def example_connect_and_get_balance():
    """Connect to IQ Option and get account balance."""
    balance = client.get_balance()
    print(f"💰 Current balance: ${balance:.2f}")
```

**Output:**
```
============================================================
EXAMPLE 1: GET BALANCE
============================================================
💰 Current balance: $9976.41
```

---

### 2. Switch Account Type

```python
def example_switch_account():
    """Switch between demo and real accounts."""
    # Switch to REAL account (be careful!)
    client.switch_account('real')
    print(f"📊 Current account: REAL")
    print(f"💰 Balance: ${client.get_balance():.2f}")
    
    # Switch back to demo
    client.switch_account('demo')
```

**Output:**
```
============================================================
EXAMPLE 2: SWITCH ACCOUNT TYPE
============================================================
⚠️ Switching to REAL account...
📊 Current account: REAL
💰 Balance: $5000.00
🔄 Switching back to DEMO...
```

---

### 3. Refill Demo Account

```python
def example_refill_demo():
    """Refill demo account (useful for testing)."""
    old_balance = client.get_balance()
    print(f"💰 Old balance: ${old_balance:.2f}")
    
    # Add $10,000 to demo account
    client.refill_demo(10000)
    
    time.sleep(1)
    new_balance = client.get_balance()
    print(f"💰 New balance: ${new_balance:.2f}")
```

**Output:**
```
============================================================
EXAMPLE 3: REFILL DEMO ACCOUNT
============================================================
💰 Old balance: $9976.41
💵 Refilling demo account +$10,000...
💰 New balance: $19976.41
```

---

### 4. Get Historical Candles

```python
def example_get_historical_candles():
    """Get historical candlestick data."""
    candles = client.get_candles("EURUSD", count=50, timeframe=60)
    
    print(f"✅ Retrieved {len(candles)} candles")
    print("\nLast 5 candles (most recent last):")
    print("-" * 70)
    print(f"{'Time':<12} {'Open':<10} {'High':<10} {'Low':<10} {'Close':<10}")
    print("-" * 70)
    
    for candle in candles[-5:]:
        time_str = datetime.fromtimestamp(candle['from']).strftime('%H:%M:%S')
        print(f"{time_str:<12} {candle['open']:<10.5f} {candle['max']:<10.5f} "
              f"{candle['min']:<10.5f} {candle['close']:<10.5f}")
```

**Output:**
```
============================================================
EXAMPLE 4: GET HISTORICAL CANDLES
============================================================
📊 Fetching EURUSD 1-minute candles...
✅ Retrieved 50 candles

Last 5 candles (most recent last):
----------------------------------------------------------------------
Time         Open       High       Low        Close     
----------------------------------------------------------------------
20:03:00     1.15881    1.15885    1.15876    1.15876   
20:04:00     1.15876    1.15880    1.15870    1.15872   
20:05:00     1.15872    1.15882    1.15870    1.15880   
```

---

### 5. Real-Time Candle Stream

```python
def example_real_time_candles():
    """Subscribe to real-time candle streams."""
    def on_candle(candle):
        print(f"🔥 NEW CANDLE: {candle.asset_name} {candle.timeframe}s")
        print(f"   Open: {candle.open:.5f}  Close: {candle.close:.5f}")
        print(f"   High: {candle.high:.5f}   Low: {candle.low:.5f}")
    
    client.on_new_candle(on_candle)
    client.start_candle_stream("EURUSD", 60)
    
    time.sleep(30)
    client.stop_candle_stream("EURUSD", 60)
```

**Output:**
```
============================================================
EXAMPLE 5: REAL-TIME CANDLE STREAM
============================================================
📡 Subscribing to EURUSD 60s candles...
✅ Subscribed! Waiting 30 seconds for candles...

🔥 NEW CANDLE: EURUSD 60s
   Open: 1.15881  Close: 1.15876
   High: 1.15885   Low: 1.15876
----------------------------------------
```

---

### 6. Get Current Price

```python
def example_get_current_price():
    """Get current price from cached candles."""
    client.start_candle_stream("EURUSD", 60)
    time.sleep(3)
    
    price = client.get_current_price("EURUSD")
    print(f"💰 EURUSD current price: {price:.5f}")
    
    candles = client.get_last_candles("EURUSD", 60, count=5)
    for i, candle in enumerate(candles):
        print(f"   Candle {i+1}: Close = {candle.close:.5f}")
    
    client.stop_candle_stream("EURUSD", 60)
```

**Output:**
```
============================================================
EXAMPLE 6: GET CURRENT PRICE
============================================================
💰 EURUSD current price: 1.15876

📊 Last 5 candles stored: 5
   Candle 1: Close = 1.15872
   Candle 2: Close = 1.15880
   Candle 3: Close = 1.15876
```

---

### 7. Place Binary Trade

```python
def example_place_binary_trade():
    """Place a binary options trade."""
    balance_before = client.get_balance()
    print(f"💰 Balance before: ${balance_before:.2f}")
    
    trade_params = OptionsTradeParams(
        asset="EURUSD",
        expiry=1,
        amount=10,
        direction=Direction.CALL,
        option_type=OptionType.BINARY_OPTION
    )
    
    success, order_id = client.execute_options_trade(trade_params)
    
    if success:
        print(f"✅ Trade placed! Order ID: {order_id}")
        time.sleep(65)
        
        success, outcome, pnl = client.get_trade_outcome(order_id, expiry=1)
        
        if success:
            balance_after = client.get_balance()
            print(f"\n📊 TRADE RESULT:")
            print(f"   Outcome: {outcome.get('result', 'unknown').upper()}")
            print(f"   P&L: ${pnl:+.2f}")
            print(f"   Balance after: ${balance_after:.2f}")
```

**Output:**
```
============================================================
EXAMPLE 7: PLACE BINARY OPTIONS TRADE
============================================================
💰 Balance before: $9976.41
📈 Placing CALL trade on EURUSD ($10)...
✅ Trade placed! Order ID: 13916614300
⏳ Waiting 65 seconds for trade result...

📊 TRADE RESULT:
   Outcome: WIN
   P&L: +$8.50
   Balance after: $9984.91
```

---

### 8. Place Digital Trade

```python
def example_place_digital_trade():
    """Place a digital options trade."""
    trade_params = OptionsTradeParams(
        asset="EURUSD",
        expiry=1,
        amount=10,
        direction=Direction.PUT,
        option_type=OptionType.DIGITAL_OPTION
    )
    
    success, order_id = client.execute_options_trade(trade_params)
    
    if success:
        print(f"✅ Digital trade placed! Order ID: {order_id}")
    else:
        print(f"❌ Trade failed: {order_id}")
```

**Output:**
```
============================================================
EXAMPLE 8: PLACE DIGITAL OPTIONS TRADE
============================================================
📉 Placing PUT trade on EURUSD ($10)...
✅ Digital trade placed! Order ID: 13916614301
```

---

### 9. Get Position History

```python
def example_get_position_history():
    """Get trading history."""
    positions = client.get_position_history_by_page(
        instrument_type=["binary-option", "turbo-option"],
        limit=10,
        offset=0
    )
    
    for pos in positions:
        pnl = pos.get('pnl_net', 0)
        result = "✅ WIN" if pnl > 0 else "❌ LOSS" if pnl < 0 else "➖ DRAW"
        print(f"   {result} | P&L: ${pnl:+.2f} | Asset: {pos.get('active_id')}")
```

**Output:**
```
============================================================
EXAMPLE 9: GET POSITION HISTORY
============================================================
📜 Fetching last 10 binary option trades...
✅ Found 10 positions
--------------------------------------------------------------------------------
   ✅ WIN | P&L: +$8.50 | Asset: 1861
   ❌ LOSS | P&L: -$10.00 | Asset: 1861
   ✅ WIN | P&L: +$8.50 | Asset: 1861
```

---

### 10. Get Filtered Positions

```python
def example_get_filtered_positions():
    """Get filtered position history with readable dates."""
    positions = client.account_manager.get_filtered_position_history(
        instrument_types=["binary-option", "turbo-option"],
        limit=20
    )
    
    print(f"{'Time':<20} {'Asset':<10} {'Result':<8} {'P&L':<10} {'Amount':<10}")
    print("-" * 65)
    
    for pos in positions:
        open_time = pos.get('open_time', 'N/A')
        pnl = pos.get('pnl_net', 0)
        result = "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "DRAW"
        result_color = "✅" if pnl > 0 else "❌" if pnl < 0 else "➖"
        
        print(f"{open_time:<20} {pos.get('active_id', 'N/A'):<10} "
              f"{result_color} {result:<5} ${pnl:+.2f}    ${pos.get('invest', 0):<10}")
```

**Output:**
```
============================================================
EXAMPLE 10: GET FILTERED POSITIONS
============================================================
✅ Found 15 positions

Time                 Asset      Result   P&L        Amount    
-----------------------------------------------------------------
2025-05-21 20:03:15  1861       ✅ WIN    +$8.50     $10.00    
2025-05-21 20:02:00  1861       ❌ LOSS   -$10.00    $10.00    
2025-05-21 20:00:45  1861       ✅ WIN    +$8.50     $10.00    
```

---

### 11. Get Underlying Assets

```python
def example_get_underlying_assets():
    """Get available trading assets."""
    forex = client.market_manager.get_underlying_assests('forex')
    print(f"✅ Found {len(forex)} Forex pairs")
    
    for asset in forex[:10]:
        print(f"   {asset['name']} (ID: {asset['active_id']})")
    
    crypto = client.market_manager.get_underlying_assests('crypto')
    print(f"\n✅ Found {len(crypto)} Crypto pairs")
    
    for asset in crypto[:5]:
        print(f"   {asset['name']} (ID: {asset['active_id']})")
```

**Output:**
```
============================================================
EXAMPLE 11: GET UNDERLYING ASSETS
============================================================
📊 Fetching Forex assets...
✅ Found 27 Forex pairs

First 10 Forex pairs:
   EURUSD (ID: 1861)
   GBPUSD (ID: 1867)
   USDJPY (ID: 1865)
   AUDUSD (ID: 1870)
   USDCAD (ID: 1878)
   
📊 Fetching Crypto assets...
✅ Found 15 Crypto pairs
   BTCUSD (ID: 1916)
   ETHUSD (ID: 1941)
   XRPUSD (ID: 2107)
```

---

### 12. Simple Trading Bot

```python
def example_simple_trading_bot():
    """Simple trading bot using candle direction."""
    print(f"💰 Starting balance: ${client.get_balance():.2f}")
    
    client.start_candle_stream("EURUSD", 60)
    
    trade_count = 0
    max_trades = 3
    
    def on_new_candle(candle):
        nonlocal trade_count
        
        if trade_count >= max_trades:
            return
        
        if candle.close > candle.open:
            direction = Direction.CALL
            direction_name = "CALL (UP)"
        else:
            direction = Direction.PUT
            direction_name = "PUT (DOWN)"
        
        trade_params = OptionsTradeParams(
            asset="EURUSD",
            expiry=1,
            amount=5,
            direction=direction,
            option_type=OptionType.BINARY_OPTION
        )
        
        success, order_id = client.execute_options_trade(trade_params)
        
        if success:
            trade_count += 1
            print(f"✅ Trade {trade_count}/{max_trades} placed (ID: {order_id})")
    
    client.candle_manager.on_new_candle_async(on_new_candle)
    
    time.sleep(max_trades * 60)
    client.stop_candle_stream("EURUSD", 60)
    print(f"\n💰 Final balance: ${client.get_balance():.2f}")
```

**Output:**
```
============================================================
EXAMPLE 12: SIMPLE TRADING BOT
============================================================
💰 Starting balance: $9976.41
🤖 Bot will trade based on candle direction

📊 Candle closed: PUT (DOWN)
   Open: 1.15881 → Close: 1.15876
📈 Placing PUT (DOWN) trade...
✅ Trade 1/3 placed (ID: 13916614302)

💰 Final balance: $9987.91
```

---

## 📚 API Reference

### IQOptionClient

| Method | Description |
|--------|-------------|
| `connect()` | Connect to IQ Option |
| `disconnect()` | Disconnect gracefully |
| `get_balance()` | Get current account balance |
| `switch_account(account_type)` | Switch between 'demo' and 'real' |
| `refill_demo(amount)` | Refill demo account |
| `start_candle_stream(asset, timeframe)` | Subscribe to real-time candles |
| `stop_candle_stream(asset, timeframe)` | Unsubscribe from candles |
| `get_current_price(asset)` | Get current price |
| `get_last_candles(asset, timeframe, count)` | Get last N candles |
| `execute_options_trade(params)` | Place a trade |
| `get_trade_outcome(order_id, expiry)` | Get trade result |
| `get_position_history_by_page(...)` | Get paginated history |
| `on_new_candle(callback)` | Register callback for new candles |

### Candle Object

| Attribute | Type | Description |
|-----------|------|-------------|
| `asset_name` | str | Asset name (e.g., "EURUSD") |
| `asset_id` | int | IQ Option internal ID |
| `timeframe` | int | Candle duration in seconds |
| `timestamp` | int | Unix timestamp |
| `open` | float | Opening price |
| `close` | float | Closing price |
| `high` | float | Highest price |
| `low` | float | Lowest price |
| `volume` | float | Trading volume |

### OptionsTradeParams

| Parameter | Type | Description |
|-----------|------|-------------|
| `asset` | str | Asset name (e.g., "EURUSD") |
| `expiry` | int | Expiry in minutes |
| `amount` | float | Trade amount in USD (min $1) |
| `direction` | Direction | `Direction.CALL` or `Direction.PUT` |
| `option_type` | OptionType | `OptionType.BINARY_OPTION` or `OptionType.DIGITAL_OPTION` |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     IQOptionClient                          │
│  (Main interface for users)                                 │
└───────────┬─────────────────────────────┬───────────────────┘
            │                             │
            ▼                             ▼
┌───────────────────────┐     ┌─────────────────────────────┐
│   WebSocketManager    │     │      AccountManager         │
│   - Connection mgmt   │     │      - Balance tracking     │
│   - Message routing   │     │      - Account switching    │
└───────────┬───────────┘     └─────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│                     MessageHandler                          │
│              Routes WebSocket messages to handlers          │
└───────────┬─────────────────────────────┬───────────────────┘
            │                             │
            ▼                             ▼
┌───────────────────────┐     ┌─────────────────────────────┐
│ CandleSubscription    │     │       TradeManager          │
│ Manager               │     │      - Trade execution      │
│ - Real-time candles   │     │      - Order confirmation   │
│ - Deque storage       │     │      - Outcome tracking     │
│ - Callback system     │     │                             │
└───────────────────────┘     └─────────────────────────────┘
```

### Data Flow

1. **WebSocket** receives messages from IQ Option
2. **MessageHandler** routes to appropriate handler
3. **CandleSubscriptionManager** processes candle data
4. **Callbacks** execute your strategy in separate threads
5. **TradeManager** executes trades and tracks outcomes

---

## 📺 YouTube Tutorial Series

This API is built and explained step-by-step in the **"Build a Complete IQ Option Trading Bot with Python"** Masterclass:

| Episode | Topic |
|---------|-------|
| EP#01 | Basic Connection & Account Management |
| EP#02 | Real-Time Candle Streaming |
| EP#03 | Binary & Digital Options Trading |
| EP#04 | Position History & Analytics |
| EP#05 | Asset Management & Market Data |
| EP#06 | Building a Simple Trading Bot |
| EP#07 | Advanced Risk Management |
| EP#08 | Data Visualization & Backtesting |

🔔 **Subscribe**: [@BytecodeAutomation](https://youtube.com/@BytecodeAutomation)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/iqoption-api.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/
```

---

## ⚠️ Disclaimer

**IMPORTANT: For educational purposes only.**

- Trading binary options involves **substantial risk of loss**
- Never trade with money you cannot afford to lose
- Past performance does **not** guarantee future results
- This software is for **educational purposes** only
- The author is **not** a financial advisor
- **Always test** on demo accounts before real trading

By using this software, you agree that:
- You are solely responsible for your trading decisions
- The author assumes no liability for financial losses
- You will comply with your local laws and regulations

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Contact & Support

- **YouTube**: [@BytecodeAutomation](https://youtube.com/@BytecodeAutomation)
- **Telegram**: [t.me/BytecodeAutomation](https://t.me/BytecodeAutomation)
- **GitHub Issues**: [Create an issue](https://github.com/yourusername/iqoption-api/issues)

---

## ⭐ Star the Project

If this project helped you, please give it a star on GitHub! It helps others discover it.

```bash
git clone https://github.com/yourusername/iqoption-api.git
cd iqoption-api
python examples.py
```

**Happy Trading!** 🚀
