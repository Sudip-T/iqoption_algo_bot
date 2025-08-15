import sys
import time
import logging
from dataclasses import dataclass
from typing import Optional, List
from version2.settings import *

logger = logging.getLogger(__name__)


@dataclass
class TournamentAccount:
    id: int
    name: str
    balance: float


class AccountManager:
    def __init__(self, websocket_manager, message_handler):
        self.available_accounts = {}
        self.active_balance_id = None
        self.ws_manager = websocket_manager
        self.message_handler = message_handler
        self.active_account_type = self._validate_account_type(DEFAULT_ACCOUNT_TYPE.lower())
    
    def set_default_account(self) -> None:
        """Initialize active balance ID from profile data"""
        if self.message_handler.profile_msg:
            balances = self.message_handler.profile_msg['msg']['balances']
            for balance in balances:
                if balance['type'] == 4:  # Demo account
                    self.available_accounts['demo'] = balance
                elif balance['type'] == 1:  # Real account
                    self.available_accounts['real'] = balance

            self.active_balance_id = self.available_accounts[self.active_account_type]['id']
            logger.info(f'Active Account - {self.active_account_type.capitalize()}, '
            f'Balance: {self.available_accounts[self.active_account_type]['amount']:.2f}'
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
            if item['type'] == self.ACCOUNT_TOURNAMENT
        ]
        
        # tournaments_accounts = []
        # for item in self.message_handler.balance_data:
        #     if item['type'] == 2:
        #         tournaments_accounts.append({
        #             'id': item['id'],
        #             'name': item['tournament_name'],
        #             'balance': item['amount']
        #         })
        # return tournaments_accounts
    
    def get_active_account_balance(self) -> Optional[float]:
        accounts = self.get_account_balances()
        print(self.active_balance_id)
        
        for account in accounts:
            if account['id'] == self.active_balance_id:
                return account['amount']
            
    def _validate_account_type(self, account_type:str) -> str:
        if account_type.lower() not in ['real', 'demo']:
            logger.error(f"{account_type} is Invalid Account Type! Needs to one of ['real', 'demo']")
            sys.exit()
        return account_type.lower()
    
    def switch_account(self, account_type: str) -> None:
        """Switch between real and demo accounts"""

        self._validate_account_type(account_type)
        accounts = self.get_account_balances()

        real_account_id, demo_account_id = None, None
        for account in accounts:
            if account['type'] == 1:
                real_account_id = account['id']
            if account['type'] == 4:
                demo_account_id = account['id']

        target_account_id = real_account_id if account_type == 'real' else demo_account_id
        self._set_portfolio_subscription(real_account_id if account_type == 'real' else demo_account_id)

        if self.active_balance_id == target_account_id:
            self.active_account_type = 'real'
            logger.info(f'Successfully switched to {account_type.capitalize()} Account (ID: {target_account_id}, Balance: {self.get_active_account_balance()})')
    
    def _set_portfolio_subscription(self, account_id:int)-> None:
        if self.active_balance_id is not None:
            self._portfolio_position_change('unsubscribeMessage', self.active_balance_id)
        
        self.active_balance_id = account_id
        self._portfolio_position_change('subscribeMessage', self.active_balance_id)
    
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