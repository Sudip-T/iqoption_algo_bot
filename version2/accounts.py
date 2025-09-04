import sys
import time
import json
import logging
from datetime import datetime
from version2.settings import *
from dataclasses import dataclass
from typing import Optional, List
from typing import List, Dict, Any
from version2.utilities import get_timestamps

logger = logging.getLogger(__name__)


@dataclass
class TournamentAccount:
    """
    Data class representing a tournament account.
    
    Attributes:
        id (int): Unique identifier for the tournament account.
        name (str): Display name of the tournament.
        balance (float): Current balance amount in the account.
    """

    id: int
    name: str
    balance: float


class AccountManager:
    """
    Manages account operations including account switching, balance tracking,
    and position history retrieval.
    
    Attributes:
        available_accounts (dict): Dictionary storing available account information.
        current_account_id (int): ID of the currently active account.
        ws_manager: WebSocket manager for communication.
        message_handler: Handler for processing incoming messages.
        current_account_type (str): Type of current account ('real' or 'demo').
    """

    def __init__(self, websocket_manager, message_handler):
        self.available_accounts = {}
        self.current_account_id = None
        self.ws_manager = websocket_manager
        self.message_handler = message_handler
        self.current_account_type = self._validate_account_type(DEFAULT_ACCOUNT_TYPE.lower(), exit=True)
    
    def set_default_account(self) -> None:
        """
        Set up the default trading account based on settings.DEFAULT_ACCOUNT_TYPE
        and subscribes to portfolio position changes for the active account.
        
        Note:
            Requires self.message_handler.profile_msg to be populated with account data.
        """
        if self.message_handler.profile_msg:
            # Extract balances/accounts information from profile message
            balances = self.message_handler.profile_msg['msg']['balances']
            for balance in balances:
                if balance['type'] == 4:  # Demo account
                    self.available_accounts['demo'] = balance
                elif balance['type'] == 1:  # Real account
                    self.available_accounts['real'] = balance

            # Set current account ID based on the configured account type
            self.current_account_id = self.available_accounts[self.current_account_type]['id']

            logger.info(f'Currently Active Account - {self.current_account_type.capitalize()}, '
            f'Balance: {self.available_accounts[self.current_account_type]['amount']:.2f}'
            )

            # Subscribe to portfolio position changes for tracking trades
            self._portfolio_position_change('subscribeMessage', self.current_account_id)

    def get_account_balances(self) -> List:
        """
        Fetch all account balances including regular and tournament accounts.
        
        Returns:
            List: List of account balance dictionaries containing account information.
            
        Note:
            This method blocks until the response is received from the server.
        """

        # Reset previous balance data
        self.message_handler.balance_data = None

        # Prepare message payload to request balance data
        # types_ids: 1=real, 4=demo, 2=tournament, 6=other
        # tournaments_statuses_ids: 3=active, 2=completed
        msg = {
                "name": "internal-billing.get-balances",
                "version": "1.0",
                "body": {
                    "types_ids": [1, 4, 2, 6],
                    "tournaments_statuses_ids": [3, 2]
                }
            }
        
        self.ws_manager.send_message("sendMessage", msg)
        
        # Wait for response with polling
        while self.message_handler.balance_data is None:
            time.sleep(0.1)
        
        return self.message_handler.balance_data
    
    def get_tournament_accounts(self) -> List[TournamentAccount]:
        """
        Retrieve all available tournament accounts by filtering accounts/balances.
        
        Returns:
            List[TournamentAccount]: List of tournament account objects with
                                   id, name, and balance information.
        """
        # First, Fetch all accounts/balances 
        self.get_account_balances()

        # Wait for balance data to be populated
        while self.message_handler.balance_data is None:
            time.sleep(0.1)

        # Filter and create TournamentAccount objects for tournament accounts
        return [
            TournamentAccount(
                id=item['id'],
                name=item['tournament_name'],
                balance=item['amount']
            )
            for item in self.message_handler.balance_data
            if item['type'] == ACCOUNT_TOURNAMENT
        ]
    
    def get_active_account_balance(self) -> Optional[float]:
        """
        Get the balance of the currently active account.
        
        Returns:
            Optional[float]: Current account balance, or None if account not found.
        """

        # Fetch all account balances
        accounts = self.get_account_balances()
        
        # Find and return balance for the current account
        for account in accounts:
            if account['id'] == self.current_account_id:
                return account['amount']
            
    def _validate_account_type(self, account_type:str, exit=False) -> str:
        """
        Validate that the account type is valid.
        
        Args:
            account_type (str): Account type to validate ('real' or 'demo').
            exit (bool): Whether to exit the program on invalid type.
            
        Returns:
            str: Lowercase account type if valid, None if invalid.
        """

        if account_type.lower() not in ['real', 'demo']:
            logger.error(f"{account_type} is Invalid Account Type! Needs to one of ['real', 'demo']")
            if exit:
                sys.exit()
            return
        return account_type.lower()
    
    def switch_account(self, account_type: str) -> None:
        """
        Switch between real and demo accounts.
        
        Changes the active account type and updates portfolio subscriptions
        to receive position updates for the new account.
        
        Args:
            account_type (str): Target account type ('real' or 'demo').
        """

        # Validate the requested account type
        if not self._validate_account_type(account_type):
            return
        
        # Get current account balances
        accounts = self.get_account_balances()

        # Find the target account ID based on account type
        target_account_id = None
        for account in accounts:
            if ((account_type.lower() == 'real' and account['type'] == 1) or 
                (account_type.lower() == 'demo' and account['type'] == 4)):
                target_account_id = account['id']
                break

        # Update portfolio subscription to new account
        self._set_portfolio_subscription(target_account_id)

        # Verify switch was successful and update current account type
        if self.current_account_id == target_account_id:
            self.current_account_type = account_type.lower()
            logger.info(f'Successfully switched to {account_type.capitalize()} Account (ID: {target_account_id}, Balance: {self.get_active_account_balance()})')
            return True
    
    def _set_portfolio_subscription(self, account_id:int)-> None:
        """
        Update portfolio subscription from/to a specific account.
        
        Unsubscribes from the current account (if any) and subscribes to
        position changes for the specified account.
        
        Args:
            account_id (int): ID of the account to subscribe to.
        """

        # Unsubscribe from current account if exists
        if self.current_account_id is not None:
            self._portfolio_position_change('unsubscribeMessage', self.current_account_id)
        
        # Update current account ID
        self.current_account_id = account_id

        # Subscribe to new account's position changes
        self._portfolio_position_change('subscribeMessage', self.current_account_id)
    
    def _portfolio_position_change(self, msg_name:str, account_id:int) -> None:
        """
        Subscribe or unsubscribe to portfolio position changes for an account.
        
        Args:
            msg_name (str): WebSocket message type ('subscribeMessage' or 'unsubscribeMessage').
            account_id (int): Account ID to subscribe/unsubscribe to.
        """
                
        # List of instrument types to monitor
        instrument_types = ['cfd', 'forex', 'crypto', 'digital-option', 'binary-option']

        # Subscribe/unsubscribe to each instrument type
        for instrument in instrument_types:
            msg = {
                "name": 'portfolio.position-changed',
                "version": "2.0",
                "params": {
                    "routingFilters": {
                        "instrument_type": str(instrument),
                        "user_balance_id": account_id
                    }
                }
            }
            self.ws_manager.send_message(msg_name, msg)
    
    def refill_demo_balance(self, amount=10000) -> None:
        """
        Refill demo account balance to specified amount.
        
        Args:
            amount (int): Amount to set as new demo balance. Defaults to 10000.
        """

        # Prepare refill message
        msg = {
            'name': 'internal-billing.reset-training-balance',
            'version': '4.0',
            'body': {
                'amount': amount,
                'user_balance_id': self.message_handler.profile_msg['msg']['balances'][-1]['id']
            }
        }
        self.ws_manager.send_message('sendMessage', msg)

        # Wait for operation to complete
        time.sleep(1)

    def get_position_history_by_page(self, instrument_type: List[str],
                                    limit: int = 300,
                                    offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve position history using pagination.
        
        Fetches trading position history for specified instrument types
        using limit and offset for pagination.
        
        Args:
            instrument_type (List[str]): List of instrument types to query.
                                       Valid types: ["marginal-forex", "marginal-cfd", 
                                       "marginal-crypto", "digital-option", "blitz-option"],
                                       ["turbo-option", "binary-option"]
            limit (int): Maximum number of positions to retrieve. Defaults to 300.
            offset (int): Number of positions to skip (for pagination). Defaults to 0.
            
        Returns:
            list: List of position dictionaries containing trading history.
        """

        # Prepare pagination-based query message
        msg = {
        "body": {
            "instrument_types": instrument_type,
            "limit": limit,
            "offset": offset,
            "user_balance_id": self.current_account_id,
            },
            "name": "portfolio.get-history-positions",
            "version": "2.0",
        }

        return self._send_position_query(msg)

    def get_position_history_by_time(self, instrument_type: List[str],
                                    start_time: Optional[str] = None,
                                    end_time: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve position history for a specific time range.
        
        Args:
            instrument_type (List[str]): List of instrument types to query.
            start_time (Optional[str]): Start time in format "YYYY-MM-DD HH:MM:SS".
                                      If None, defaults to 24 hours ago.
            end_time (Optional[str]): End time in format "YYYY-MM-DD HH:MM:SS".
                                    If None, defaults to current time.
            
        Returns:
            list: List of position dictionaries containing trading history.
        """

        # Convert datetime strings to timestamps
        start_ts, end_ts = get_timestamps(start_time, end_time)

        # Prepare time-based query message
        msg = {
            "body": {
                "end": end_ts,
                "instrument_types": instrument_type,
                "start": start_ts,
                "user_balance_id": self.current_account_id,
            },
            "name": "portfolio.get-history-positions",
            "version": "2.0",
        }

        return self._send_position_query(msg)
    

    def _send_position_query(self, msg: dict) -> list:
        """       
        Handles the WebSocket communication for position history queries,
        including timeout management and response waiting.
        
        Args:
            msg (dict): WebSocket message dictionary to send.
            
        Returns:
            list: List of position history data received from server.
            
        Raises:
            TimeoutError: If no response received within timeout period.
        """

        # Reset previous response data
        self.message_handler.hisory_positions = None
    
        self.ws_manager.send_message("sendMessage", msg)
        
        # Wait for response with timeout protection
        timeout = 10
        start_wait = time.time()
        while self.message_handler.hisory_positions is None:
            if time.time() - start_wait > timeout:
                raise TimeoutError("Timeout waiting for position history response")
            time.sleep(0.1)
        
        return self.message_handler.hisory_positions
    


    # Add this method to your AccountManager class
    def get_filtered_position_history(self, instrument_types: List[str] = ["turbo-option", "binary-option"], 
                                    limit: int = 300, offset: int = 0) -> List[Dict[str, Any]]:
        """       
        Retrieves position history and filters out only the relevant fields,
        converting timestamps to readable datetime format.
        
        Args:
            instrument_types (List[str]): List of instrument types to query.
                                        Defaults to ["turbo-option", "binary-option"].
            limit (int): Maximum number of positions to retrieve. Defaults to 300.
            offset (int): Offset for pagination. Defaults to 0.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries with filtered position data
                                containing: pnl_net, close_profit, close_reason, status,
                                invest, source, active_id, open_time, close_time.
        """

        # Get raw position history data
        positions = self.get_position_history_by_page(instrument_types, limit, offset)
        
        filtered_data = []
        for position in positions:
            # Extract only the fields we need
            filtered_position = {
                'pnl_net': position.get('pnl_net'),
                'close_profit': position.get('close_profit'),
                'close_reason': position.get('close_reason'),
                'status': position.get('status'),
                'invest': position.get('invest'),
                'source': position.get('instrument_type'),
                'active_id': position.get('active_id'),
            }

            # Convert open_time from milliseconds to readable format
            if position.get('open_time'):
                timestamp = position['open_time'] / 1000  # Convert ms to seconds
                filtered_position['open_time'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

            # Convert close_time from milliseconds to readable format
            if position.get('close_time'):
                timestamp = position['close_time'] / 1000  # Convert ms to seconds
                filtered_position['close_time'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

            filtered_data.append(filtered_position)
        
        return filtered_data

    def save_filtered_positions_to_file(self, filename: str = 'positions.json', 
                                    instrument_types: List[str] = ["turbo-option", "binary-option"],
                                    limit: int = 300, offset: int = 0) -> None:
        """        
        Retrieves filtered position history and saves it to a JSON file
        for external analysis or record keeping.
        
        Args:
            filename (str): Name of the output file. Defaults to 'positions.json'.
            instrument_types (List[str]): List of instrument types to query.
                                        Defaults to ["turbo-option", "binary-option"].
            limit (int): Maximum number of positions to retrieve. Defaults to 300.
            offset (int): Offset for pagination. Defaults to 0.
        """

        # Get filtered position data
        filtered_data = self.get_filtered_position_history(instrument_types, limit, offset)
        
        # Save data to JSON file with proper formatting
        with open(filename, 'w') as file:
            json.dump(filtered_data, file, indent=4)
        
        logger.info(f"Saved {len(filtered_data)} positions to {filename}")