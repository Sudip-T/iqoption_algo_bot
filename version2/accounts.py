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
    id: int
    name: str
    balance: float


class AccountManager:
    def __init__(self, websocket_manager, message_handler):
        self.available_accounts = {}
        self.current_account_id = None
        self.ws_manager = websocket_manager
        self.message_handler = message_handler
        self.current_account_type = self._validate_account_type(DEFAULT_ACCOUNT_TYPE.lower(), exit=True)
    
    def set_default_account(self) -> None:
        if self.message_handler.profile_msg:
            balances = self.message_handler.profile_msg['msg']['balances']
            for balance in balances:
                if balance['type'] == 4:  # Demo account
                    self.available_accounts['demo'] = balance
                elif balance['type'] == 1:  # Real account
                    self.available_accounts['real'] = balance

            self.current_account_id = self.available_accounts[self.current_account_type]['id']
            logger.info(f'Active Account - {self.current_account_type.capitalize()}, '
            f'Balance: {self.available_accounts[self.current_account_type]['amount']:.2f}'
            )
    
    def get_account_balances(self) -> List:
        """Fetch all account balances including tournament accounts"""
        self.message_handler.balance_data = None
        msg = {
                "name": "internal-billing.get-balances",
                "version": "1.0",
                "body": {
                    "types_ids": [1, 4, 2, 6],
                    "tournaments_statuses_ids": [3, 2]
                }
            }
        
        self.ws_manager.send_message("sendMessage", msg)
        
        while self.message_handler.balance_data is None:
            time.sleep(0.1)
        
        return self.message_handler.balance_data
    
    def get_tournament_accounts(self) -> List[TournamentAccount]:
        self.get_account_balances()
        while self.message_handler.balance_data is None:
            time.sleep(0.1)

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
        accounts = self.get_account_balances()
        
        for account in accounts:
            if account['id'] == self.current_account_id:
                return account['amount']
            
    def _validate_account_type(self, account_type:str, exit=False) -> str:
        if account_type.lower() not in ['real', 'demo']:
            logger.error(f"{account_type} is Invalid Account Type! Needs to one of ['real', 'demo']")
            if exit:
                sys.exit()
            return
        return account_type.lower()
    
    def switch_account(self, account_type: str) -> None:
        """Switch between real and demo accounts"""

        if not self._validate_account_type(account_type):
            return
        accounts = self.get_account_balances()

        target_account_id = None
        for account in accounts:
            if ((account_type.lower() == 'real' and account['type'] == 1) or 
                (account_type.lower() == 'demo' and account['type'] == 4)):
                target_account_id = account['id']
                break

        self._set_portfolio_subscription(target_account_id)

        # Verify switch and update current account type
        if self.current_account_id == target_account_id:
            self.current_account_type = account_type.lower()
            logger.info(f'Successfully switched to {account_type.capitalize()} Account (ID: {target_account_id}, Balance: {self.get_active_account_balance()})')
    
    def _set_portfolio_subscription(self, account_id:int)-> None:
        if self.current_account_id is not None:
            self._portfolio_position_change('unsubscribeMessage', self.current_account_id)
        
        self.current_account_id = account_id
        self._portfolio_position_change('subscribeMessage', self.current_account_id)
    
    def _portfolio_position_change(self, msg_name:str, account_id:int) -> None:
        instrument_types = ['cfd', 'forex', 'crypto', 'digital-option', 'binary-option']
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
        msg = {
            'name': 'internal-billing.reset-training-balance',
            'version': '4.0',
            'body': {
                'amount': amount,
                'user_balance_id': self.message_handler.profile_msg['msg']['balances'][-1]['id']
            }
        }
        self.ws_manager.send_message('sendMessage', msg)
        time.sleep(1)

    def get_position_history_by_page(self, instrument_type: List[str],
                                    limit: int = 300,
                                    offset: int = 0) -> list:
        # valid_instruement = ["marginal-forex", "marginal-cfd", "marginal-crypto", "digital-option", 
        # "blitz-option"], ["turbo-option", "binary-option"]
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
                                    end_time: Optional[str] = None):
        
        start_ts, end_ts = get_timestamps(start_time, end_time)
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
        """Common method to send query and wait for response"""
        # Reset previous response
        self.message_handler.hisory_positions = None
    
        self.ws_manager.send_message("sendMessage", msg)
        
        # Wait for response with timeout
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
        Get filtered position history with specific fields and formatted timestamps
        
        Args:
            instrument_types: List of instrument types to query
            limit: Maximum number of positions to retrieve
            offset: Offset for pagination
        
        Returns:
            List of dictionaries with filtered position data
        """
        positions = self.get_position_history_by_page(instrument_types, limit, offset)
        
        filtered_data = []
        for position in positions:
            filtered_position = {
                'pnl_net': position.get('pnl_net'),
                'close_profit': position.get('close_profit'),
                'close_reason': position.get('close_reason'),
                'status': position.get('status'),
                'invest': position.get('invest'),
                'source': position.get('instrument_type'),
                'active_id': position.get('active_id'),
            }

            if position.get('open_time'):
                timestamp = position['open_time'] / 1000  # Convert ms to seconds
                filtered_position['open_time'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

            if position.get('close_time'):
                timestamp = position['close_time'] / 1000  # Convert ms to seconds
                filtered_position['close_time'] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

            filtered_data.append(filtered_position)
        
        return filtered_data

    def save_filtered_positions_to_file(self, filename: str = 'positions.json', 
                                    instrument_types: List[str] = ["turbo-option", "binary-option"],
                                    limit: int = 300, offset: int = 0) -> None:
        """
        Get filtered position history and save to JSON file
        
        Args:
            filename: Name of the output file
            instrument_types: List of instrument types to query
            limit: Maximum number of positions to retrieve
            offset: Offset for pagination
        """
        filtered_data = self.get_filtered_position_history(instrument_types, limit, offset)
        
        with open(filename, 'w') as file:
            json.dump(filtered_data, file, indent=4)
        
        logger.info(f"Saved {len(filtered_data)} positions to {filename}")