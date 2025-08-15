import sys
import time
import logging
import requests
from version2.settings import *
from version2.wsmanager.iqwebsocket import WebSocketManager
from version2.wsmanager.message_handler import MessageHandler
from version2.accounts import AccountManager
from version2.markets import MarketManager


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IQOptionAlgoAPI:
    def __init__(self, email=None, password=None, account_type=None):
        self.email = email or EMAIL
        self.password = password or PASSWORD
        self.account_mode = account_type or DEFAULT_ACCOUNT_TYPE
        self.session = requests.Session()
        self._connected = False

        self.message_handler = MessageHandler()
        self.websocket = WebSocketManager(
            WS_URL,
            self.message_handler
        )
        self.account_manager = AccountManager(self.websocket, self.message_handler)
        self.market_manager = MarketManager(self.websocket, self.message_handler)
        logger.info('ALGO BOT initialized successfully')


    def c2as_login(self):
        """Login and establish websocket connection"""
        if not all([ self.email, self.password]):
            print("Email and password are required!")
            sys.exit()

        try:
            response = self.session.post(url=LOGIN_URL, 
                data={'identifier': self.email,'password': self.password})
            response.raise_for_status()

            if self.get_session_id():
                logger.info(f'Successfully logged into an account - SSID: {self.get_session_id()}')
                return True
        except Exception as e:
            logger.warning(e)

    
    def c2as_logout(self, data=None):
        if self.session.post(url=LOGOUT_URL, data=data).status_code == 200:
            self._connected = False
            logger.info(f'Logged out Successfully')
    
    def get_session_id(self):
        return self.session.cookies.get('ssid')
    
    def _connect(self):
        """Login and establish websocket connection"""
        if self.c2as_login():
            self.websocket.start_websocket()

            # websocket authentication by passing SSID
            self.websocket.send_message('ssid', self.get_session_id())

            # Wait for profile message to confirm being authenticated
            while self.message_handler.profile_msg is None:
                time.sleep(.1)

            self.account_manager.set_default_account()
            self._connected = True
    
    # Expose manager methods for convenience
    def get_current_account_balance(self):
        self._ensure_connected()
        return self.account_manager.get_active_account_balance()
    
    def refill_demo_account(self, amount=10000):
        self._ensure_connected()
        return self.account_manager.refill_demo_balance(amount)
    
    def get_tournament_accounts(self):
        self._ensure_connected()
        return self.account_manager.get_tournament_accounts()
    
    def switch_account(self, account_type:str):
        self._ensure_connected()
        if account_type == self.account_manager.active_account_type:
            logger.warning(f'Already switched to {account_type}!')
            return
        return self.account_manager.switch_account(account_type)
    
    def get_candle_history(self, asset_name='EURUSD-op', count=50, timeframe=60):
        self._ensure_connected()
        return self.market_manager.get_candle_history(asset_name, count, timeframe)
    
    def plot_candles(self, candles_data=None):
        return self.market_manager.plot_candles(candles_data)
    
    def save_candles_to_csv(self, candles_data=None, filename='candles'):
        return self.market_manager.save_candles_to_csv(candles_data, filename)
    
    def _ensure_connected(self):
        """Ensure bot is connected."""
        if not self._connected:
            raise Exception("Bot is not connected. Call connect() first.")
