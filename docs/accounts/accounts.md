# AccountManager Documentation

## Overview
The AccountManager module provides comprehensive account management functionality for trading platforms, including support for real, demo, and tournament accounts. It handles account switching, balance retrieval, and portfolio subscriptions through WebSocket communication.

## Dependencies
```python
import sys
import time
import logging
from dataclasses import dataclass
from typing import Optional, List
from version2.settings import *
```

## Classes

### TournamentAccount
A dataclass representing a tournament account with basic information.

**Attributes:**
- `id` (int): Unique identifier for the tournament account
- `name` (str): Name of the tournament
- `balance` (float): Current balance in the tournament account

```python
@dataclass
class TournamentAccount:
    id: int
    name: str
    balance: float
```

### AccountManager
Main class for managing trading accounts, including real, demo, and tournament accounts.

#### Constructor
```python
def __init__(self, websocket_manager, message_handler):
```

**Parameters:**
- `websocket_manager`: WebSocket manager instance for sending messages
- `message_handler`: Message handler instance for processing responses

**Initialization:**
- Sets up empty available accounts dictionary
- Initializes current account ID as None
- Stores references to WebSocket manager and message handler
- Validates and sets the default account type from settings

## Methods

### set_default_account()
Sets up the default account based on settinge.DEFAULT_ACCOUNT_TYPE

```python
def set_default_account() -> None:
```

**Functionality:**
- Extracts balance information from profile message
- Identifies demo accounts (type 4) and real accounts (type 1)
- Sets the current account ID based on the default account type
- Logs the active account information

**Usage Example:**
```python
account_manager = AccountManager(ws_manager, msg_handler)
account_manager.set_default_account()
```

### get_account_balances()
Retrieves all account balances including tournament accounts.

```python
def get_account_balances() -> List:
```

**Returns:** List of account balance dictionaries

**Message Structure:**
```python
{
    "name": "internal-billing.get-balances",
    "version": "1.0",
    "body": {
        "types_ids": [1, 4, 2, 6],  # Real, Demo, Tournament types
        "tournaments_statuses_ids": [3, 2]
    }
}
```

**Usage Example:**
```python
balances = account_manager.get_account_balances()
for balance in balances:
    print(f"Account ID: {balance['id']}, Balance: {balance['amount']}")
```

### get_tournament_accounts()
Retrieves all available tournament accounts.

```python
def get_tournament_accounts() -> List[TournamentAccount]:
```

**Returns:** List of TournamentAccount objects

**Functionality:**
- Calls `get_account_balances()` to fetch all accounts
- Filters accounts by tournament type (`ACCOUNT_TOURNAMENT`)
- Creates TournamentAccount objects with id, name, and balance

**Usage Example:**
```python
tournaments = account_manager.get_tournament_accounts()
for tournament in tournaments:
    print(f"Tournament: {tournament.name}, Balance: {tournament.balance}")
```

### get_active_account_balance()
Gets the current balance of the active account.

```python
def get_active_account_balance() -> Optional[float]:
```

**Returns:** Current account balance or None if account not found

**Usage Example:**
```python
current_balance = account_manager.get_active_account_balance()
if current_balance is not None:
    print(f"Current balance: ${current_balance:.2f}")
```

### switch_account()
Switches between real and demo accounts.

```python
def switch_account(self, account_type: str) -> None:
```

**Parameters:**
- `account_type` (str): Either "real" or "demo"

**Functionality:**
- Validates the account type
- Retrieves current account balances
- Finds the target account ID based on type
- Updates portfolio subscriptions
- Logs successful switch with account details

**Usage Example:**
```python
# Switch to demo account
account_manager.switch_account("demo")

# Switch to real account
account_manager.switch_account("real")
```

### refill_demo_balance()
Refills the demo account balance.

```python
def refill_demo_balance(self, amount=10000) -> None:
```

**Parameters:**
- `amount` (int, optional): Amount to refill (default: 10000)

**Message Structure:**
```python
{
    'name': 'internal-billing.reset-training-balance',
    'version': '4.0',
    'body': {
        'amount': amount,
        'user_balance_id': demo_account_id
    }
}
```

**Usage Example:**
```python
# Refill with default amount (10000)
account_manager.refill_demo_balance()

# Refill with custom amount
account_manager.refill_demo_balance(50000)
```

## Private Methods

### _validate_account_type()
Validates account type input.

```python
def _validate_account_type(self, account_type: str, exit=False) -> str:
```

**Parameters:**
- `account_type` (str): Account type to validate
- `exit` (bool): Whether to exit program on invalid type

**Returns:** Lowercase account type string or None if invalid

### _set_portfolio_subscription()
Manages portfolio position subscriptions for account switching.

```python
def _set_portfolio_subscription(self, account_id: int) -> None:
```

**Functionality:**
- Unsubscribes from current account portfolio updates
- Sets new current account ID
- Subscribes to new account portfolio updates

### _portfolio_position_change()
Handles portfolio position subscription/unsubscription.

```python
def _portfolio_position_change(self, msg_name: str, account_id: int) -> None:
```

**Parameters:**
- `msg_name` (str): Either "subscribeMessage" or "unsubscribeMessage"
- `account_id` (int): Account ID for subscription

**Instrument Types Covered:**
- cfd
- forex
- crypto
- digital-option
- binary-option

## Usage Flow Example

```python
# Initialize AccountManager
ws_manager = WebSocketManager()
msg_handler = MessageHandler()
account_manager = AccountManager(ws_manager, msg_handler)

# Set up default account
account_manager.set_default_account()

# Get all account balances
balances = account_manager.get_account_balances()
print(f"Found {len(balances)} accounts")

# Get tournament accounts
tournaments = account_manager.get_tournament_accounts()
for tournament in tournaments:
    print(f"Tournament: {tournament.name}")

# Switch to demo account
account_manager.switch_account("demo")

# Check current balance
balance = account_manager.get_active_account_balance()
print(f"Demo balance: ${balance:.2f}")

# Refill demo account if needed
if balance < 1000:
    account_manager.refill_demo_balance(10000)

# Switch back to real account
account_manager.switch_account("real")
```

## Error Handling

The AccountManager includes several error handling mechanisms:

1. **Account Type Validation**: Ensures only "real" or "demo" account types are accepted
2. **Logging**: Comprehensive logging for account operations and errors
3. **Graceful Exits**: Option to exit program on critical validation failures
4. **Null Checks**: Proper handling of None values and missing data

## Configuration

The module relies on settings from `version2.settings`:
- `DEFAULT_ACCOUNT_TYPE`: Default account type to use
- `ACCOUNT_TOURNAMENT`: Constant for tournament account type identification

## Notes

- All WebSocket communications are asynchronous and include waiting loops for responses
- Portfolio subscriptions are automatically managed during account switches
- Tournament accounts are read-only through this interface
- Demo account refilling is limited to demo accounts only