import sys
import time
import logging
import requests
from version2.settings import *
from typing import Optional, List

from version2.trade import TradeManager
from version2.markets import MarketManager
from version2.accounts import AccountManager
from version2.wsmanager.iqwebsocket import WebSocketManager
from version2.wsmanager.message_handler import MessageHandler

# Setup logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IQOptionAlgoAPI:
    """
    Main API class for IQOption automated trading.
    
    Provides a unified interface for account management, market data,
    and trade execution through websocket connections.
    """
    def __init__(self, email=None, password=None, account_type=None):
        """
        Initialize the IQOption API client.
        
        Args:
            email (str, optional): Login email. Defaults to settings.EMAIL
            password (str, optional): Login password. Defaults to settings.PASSWORD  
            account_type (str, optional): Account type. Defaults to settings.DEFAULT_ACCOUNT_TYPE
        """
        self.email = email or EMAIL
        self.password = password or PASSWORD
        self.account_mode = account_type or DEFAULT_ACCOUNT_TYPE

        # Initialize HTTP session for login requests
        self.session = requests.Session()
        self._connected = False

        # Initialize core managers
        self.message_handler = MessageHandler()
        self.websocket = WebSocketManager(self.message_handler)
        self.account_manager = AccountManager(self.websocket, self.message_handler)
        self.market_manager = MarketManager(self.websocket, self.message_handler)
        self.trade_manager = TradeManager(self.websocket, self.message_handler, self.account_manager)
        logger.info('ALGO BOT initialized successfully')

    def _login(self):
        """
        Authenticate with IQOption using email/password.
        
        Returns:
            bool: True if login successful, None otherwise
        """

        # Validate required credentials
        if not all([ self.email, self.password]):
            print("Email and password are required!")
            sys.exit()

        if self._connected:
            logger.warning('Already connected to iqoption')
            return

        try:
            # Send login request
            response = self.session.post(url=LOGIN_URL, 
                data={'identifier': self.email,'password': self.password})
            response.raise_for_status()

            # Check if session ID was received (login success indicator)
            if self.get_session_id():
                logger.info(f'Successfully logged into an account - SSID: {self.get_session_id()}')
                return True
        except Exception as e:
            logger.warning(e)

    
    def _logout(self, data=None):
        """
        Log out from IQOption and close session.
        
        Args:
            data (dict, optional): Additional logout data
        """
        if self.session.post(url=LOGOUT_URL, data=data).status_code == 200:
            self._connected = False
            logger.info(f'Logged out Successfully')
    
    def get_session_id(self):
        """
        Get the current session ID (SSID) from cookies.
        
        Returns:
            str: Session ID if available, None otherwise
        """
        return self.session.cookies.get('ssid')
    
    def _connect(self):
        """
        Establish full connection: login + websocket + authentication.
        
        Sets up the complete connection pipeline including websocket
        authentication and account initialization.
        """
        if self._login():
            # Start websocket connection
            self.websocket.start_websocket()

            # Authenticate websocket using session ID
            self.websocket.send_message('ssid', self.get_session_id())

            ## Wait for profile confirmation (indicates successful auth)
            while self.message_handler.profile_msg is None:
                time.sleep(.1)

            # Set default account and mark as connected
            self.account_manager.set_default_account()
            self._connected = True
    
    # Expose manager methods for convenience
    def get_current_account_balance(self):
        """
        Get the balance of the currently active account.
        
        Returns:
            float: Current account balance
        """
        self._ensure_connected()
        return self.account_manager.get_active_account_balance()
    
    def refill_demo_account(self, amount=10000):
        """
        Refill demo account with specified amount.
        
        Args:
            amount (int): Amount to add to demo account. Defaults to 10000
            
        Returns:
            bool: True if refill successful
        """
        self._ensure_connected()
        return self.account_manager.refill_demo_balance(amount)
    
    def get_tournament_accounts(self):
        """
        Retrieve list of available tournament accounts.
        
        Returns:
            list: Available tournament accounts
        """
        self._ensure_connected()
        return self.account_manager.get_tournament_accounts()
    
    def switch_account(self, account_type:str):
        """
        Switch to a different account type (demo/real/tournament).
        
        Args:
            account_type (str): Target account type
            
        Returns:
            bool: True if switch successful, False if already on target account
        """
        self._ensure_connected()
        if account_type.lower() == self.account_manager.current_account_type:
            logger.warning(f'Already on {account_type.lower()} account. No switch needed.')
            return False  # or True, depending on how you want to handle this
        return self.account_manager.switch_account(account_type)
    
    # Market Data Methods
    def get_candle_history(self, asset_name='EURUSD-op', count=50, timeframe=60):
        """
        Retrieve historical candlestick data for an asset.
        
        Args:
            asset_name (str): Asset symbol. Defaults to 'EURUSD-op'
            count (int): Number of candles to retrieve. Defaults to 50
            timeframe (int): Timeframe in seconds. Defaults to 60
            
        Returns:
            list: Historical candle data
        """
        self._ensure_connected()
        return self.market_manager.get_candle_history(asset_name, count, timeframe)
    
    def save_candles_to_csv(self, candles_data=None, filename='candles'):
        """
        Export candlestick data to CSV file.
        
        Args:
            candles_data (list, optional): Candle data to export
            filename (str): Output filename. Defaults to 'candles'
            
        Returns:
            bool: True if save successful
        """
        return self.market_manager.save_candles_to_csv(candles_data, filename)
    
    def _ensure_connected(self):
        """
        Verify that the bot is connected before executing operations.
        
        Raises:
            Exception: If bot is not connected
        """
        if not self._connected:
            raise Exception("Bot is not connected. Call connect() first.")
        
    def get_position_history_by_time(self, instrument_type: List[str],
                                    start_time: Optional[str] = None,
                                    end_time: Optional[str] = None):
        """
        Retrieve position history within a specific time range.
        
        Args:
            instrument_type (List[str]): Types of instruments to include
            start_time (str, optional): Start time filter
            end_time (str, optional): End time filter
            
        Returns:
            list: Position history within specified time range
        """
        self._ensure_connected()
        return self.account_manager.get_position_history_by_time(instrument_type, start_time=start_time, end_time=end_time)
    
    def get_position_history_by_page(self, instrument_type: List[str],
                                    limit: int = 300,
                                    offset: int = 0):
        """
        Retrieve paginated position history.
        
        Args:
            instrument_type (List[str]): Types of instruments to include
            limit (int): Maximum records per page. Defaults to 300
            offset (int): Number of records to skip. Defaults to 0
            
        Returns:
            list: Paginated position history
        """
        self._ensure_connected()
        return self.account_manager.get_position_history_by_page(instrument_type, limit=limit, offset=offset)
    
    def execute_digital_option_trade(self,asset: str,amount: int,direction: str,
                                    expiry: Optional[int] = 1):
        """
        Execute a digital options trade.
        
        Args:
            asset (str): Asset symbol to trade
            amount (int): Trade amount
            direction (str): Trade direction ('call' or 'put')
            expiry (int, optional): Expiry time in minutes. Defaults to 1
            
        Returns:
            dict: Trade execution result with order ID
        """
        self._ensure_connected()
        return self.trade_manager._execute_digital_option_trade(asset, amount, direction, expiry=expiry)
    
    def get_trade_outcome(self, order_id: int ,expiry:int):
        """
        Get the outcome of a completed trade.
        
        Args:
            order_id (int): ID of the trade order
            expiry (int): Expiry time in minutes
            
        Returns:
            dict: Trade outcome (win/loss/refund) and payout details
        """
        self._ensure_connected()
        return self.trade_manager.get_trade_outcome(order_id, expiry=expiry)
