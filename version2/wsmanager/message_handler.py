import json
import logging

logger = logging.getLogger(__name__)


class MessageHandler:
    """
    Handles various types of messages received from IQ Option Websocket.
    """
    def __init__(self):
        """
        Initialize the MessageHandler with default values for all message types.
        
        Sets up storage for profile data, balance information, market data, and position tracking.
        """
        self.server_time = None

        # User profile and account information
        self.profile_msg = None
        self.balance_data = None

        # Market and time data
        self.candles = None
        self.underlying_list = None
        self.initialization_data = None
        self._underlying_assests = None

        # Position tracking
        self.hisory_positions = None
        self.open_positions = {
            'digital_options':{},
            'binary_options':{}
        }
        self.position_info = {}
        
    def handle_message(self, message):
        """
        Route incoming messages to appropriate handler method based on message name.
        
        Args:
            message (dict): The incoming message containing 'name' and other data
        """
        message_name = message.get('name')

        # Map message names to their corresponding handler methods
        handlers = {
            'profile': self._handle_profile,
            'candles': self._handle_candles,
            'balances': self._handle_balances,
            'timeSync': self._handle_server_time,
            'underlying-list': self._handle_underlying_list,
            'initialization-data': self._handle_initialization_data,
            'training-balance-reset': self._handle_training_balance_reset,
            "history-positions":self._handle_position_history,
            "digital-option-placed":self._handle_digital_option_placed,

            "position-changed":self._handle_position_changed,
        }

        # Get the appropriate handler and invoke it if found
        handler = handlers.get(message_name)
        if handler:
            handler(message)
    
    def _handle_server_time(self, message):
        """
        Handle server time synchronization messages.
        
        Args:
            message (dict): Message containing server time information in 'msg' field
        """
        self.server_time = message['msg']
    
    def _handle_profile(self, message):
        """
        Handle user profile messages and extract active balance ID for demo account.
        
        Processes profile data and identifies the demo account balance ID (type 4).
        Real account balance has type 1, demo account has type 4.
        
        Args:
            message (dict): Profile message containing user account information and balances
        """
        self.profile_msg = message
        balances = message['msg']['balances']

        # Find demo account balance (type 4) and set as active
        for balance in balances:
            if balance['type'] == 4:  # Demo account | 1 for real, 4 for demo
                self.active_balance_id = balance['id']
                break
    
    def _handle_balances(self, message):
        """
        Handle balance update messages.
        
        Args:
            message (dict): Message containing current balance information
        """
        self.balance_data = message['msg']
    
    def _handle_training_balance_reset(self, message):
        """
        Handle demo account balance reset responses.
        
        Logs the result of balance reset operations with appropriate log levels
        based on the status code received.
        
        Args:
            message (dict): Response message from balance reset request
                          Contains 'status' field and optional error message
        """
        if message['status'] == 2000: # Success status code
            logger.info('Demo Acoount Balance Reset Successfully')
        elif message['status'] == 4001: # Error status code
            logger.warning(message['msg']['message'])
        else:
            logger.info(message)
    
    def _handle_initialization_data(self, message):
        """
        Handle platform initialization data.
        
        Args:
            message (dict): Initialization message containing underlying assets and platform data
        """
        self._underlying_assests = message['msg']
    
    def _handle_candles(self, message):
        """
        Handle candlestick/OHLCV price data messages.
        
        Args:
            message (dict): Message containing candle data in 'msg.candles' field
        """
        self.candles = message['msg']['candles']
    
    def _handle_underlying_list(self, message):
        """
        Handle underlying asset list messages.
        
        Processes different types of underlying asset lists based on the message type.
        Digital options and other instrument types may have different data structures.
        
        Args:
            message (dict): Message containing underlying asset information
        """
        if message['msg'].get('type', None) == 'digital-option':
            # Digital options have underlying assets in 'underlying' field
            self._underlying_assests = message['msg']['underlying']
        else:
            # marginal instrument types have assets in 'items' field
            self._underlying_assests = message['msg']['items']

    def _save_data(self, message, filename):
        """
        Utility method to save message data to a JSON file.
        
        Args:
            message (dict): The message data to save
            filename (str): The filename (without .json extension) to save to
        """
        with open(f'{filename}.json', 'w') as file:
            json.dump(message, file, indent=4)



    # def _handle_candles_generated(self, message):
    #     """
    #     Handle real-time tick/candle generation messages.
    #     
    #     This method is commented out but would handle real-time price updates
    #     with thread-safe tick data storage and timestamp management.
    #     """
    #     with self.tick_lock:
    #         # Store the raw tick data
    #         self.latest_tick = message.get('msg', {})
    #         # Add current timestamp if not present
    #         if 'at' not in self.latest_tick:
    #             self.latest_tick['at'] = int(time.time() * 1e9)

        
    def _handle_position_history(self, message):
        """
        Handle historical position data messages.
        
        Args:
            message (dict): Message containing historical position data in 'msg.positions' field
        """
        self.hisory_positions = message['msg']['positions']

    def _handle_digital_option_placed(self, message):
        """
        Handle digital option placement confirmation messages.
        
        Stores the option ID or error message based on the placement result.
        Uses request_id as the key to track placement requests.
        
        Args:
            message (dict): Placement confirmation containing either option ID or error message
        """
        if message["msg"].get("id") != None: # Successful placement - store the option ID
            self.open_positions['digital_options'][message["request_id"]] = message["msg"].get("id")
        else: # Failed placement - store the error message
            self.open_positions['digital_options'][message["request_id"]] = message["msg"].get("message")

    def _handle_position_changed(self, message):
        """
        Handle position status change messages.
        
        Updates position information and saves the latest position data to file.
        Uses the first order ID from the raw event as the key for tracking.
        
        Args:
            message (dict): Position change message containing updated position status
        """
        
        self.position_info[int(message["msg"]["raw_event"]["order_ids"][0])] = message['msg']

        # Save position data to file for debugging/logging purposes
        self._save_data(message['msg'], 'positions')