import json
import logging

logger = logging.getLogger(__name__)


class MessageHandler:
    def __init__(self):
        # self.algobot = algobot
        self.profile_msg = None
        self.balance_data = None
        self.server_time = None
        self.candles = None
        self.underlying_list = None
        self.initialization_data = None
        self._underlying_assests = None
        
    def handle_message(self, message):
        message_name = message.get('name')
        
        handlers = {
            'profile': self._handle_profile,
            'candles': self._handle_candles,
            'balances': self._handle_balances,
            'server_time': self._handle_server_time,
            'underlying-list': self._handle_underlying_list,
            'initialization-data': self._handle_initialization_data,
            'training-balance-reset': self._handle_training_balance_reset,
        }
        
        handler = handlers.get(message_name)
        if handler:
            handler(message)
    
    def _handle_server_time(self, message):
        self.server_time = message['msg']
    
    def _handle_profile(self, message):
        self.profile_msg = message
        balances = message['msg']['balances']
        for balance in balances:
            if balance['type'] == 4:  # Demo account | 1 for real, 4 for demo
                self.active_balance_id = balance['id']
                break
    
    def _handle_balances(self, message):
        self.balance_data = message['msg']
    
    def _handle_training_balance_reset(self, message):
        if message['status'] == 2000:
            logger.info('Demo Acoount Balance Reset Successfully')
        elif message['status'] == 4001:
            logger.warning(message['msg']['message'])
        else:
            logger.info(message)
    
    def _handle_initialization_data(self, message):
        self._underlying_assests = message['msg']
    
    def _handle_candles(self, message):
        self.candles = message['msg']['candles']
    
    def _handle_underlying_list(self, message):
        if message['msg'].get('type', None) == 'digital-option':
            self._underlying_assests = message['msg']['underlying']
        else:
            self._underlying_assests = message['msg']['items']

    def _save_data(self, message, filename):
        with open(f'{filename}.json', 'w') as file:
            json.dump(message, file, indent=4)