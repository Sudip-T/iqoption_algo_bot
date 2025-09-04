import time
import logging
from datetime import datetime, UTC
from options_assests import UNDERLYING_ASSESTS
from version2.utilities import get_expiration, get_remaining_secs

logger = logging.getLogger(__name__)


# Custom exceptions for better error categorization
class TradeExecutionError(Exception):
    """Base exception for trade execution errors"""
    pass

class InvalidTradeParametersError(TradeExecutionError):
    """Raised when trade parameters are invalid"""
    pass


class TradeManager:
    """
    Manages IQOption trading operations
    
    Handles trade parameter validation, order execution, confirmation waiting,
    and trade outcome tracking.
    """
    def __init__(self, websocket_manager, message_handler, account_manager):
        self.ws_manager = websocket_manager
        self.message_handler = message_handler
        self.account_manager = account_manager

    def get_asset_id(self, asset_name: str) -> int:
        """
        Get numeric asset ID for trading asset name.
        
        Args:
            asset_name: Trading asset name (e.g., 'EURUSD-op', 'EURUSD-OTC')
            
        Returns:
            Asset ID for API calls
            
        Raises:
            KeyError: If asset not found
        """
        if asset_name in UNDERLYING_ASSESTS:
            return UNDERLYING_ASSESTS[asset_name]
        raise KeyError(f'{asset_name} not found!')

    def _execute_digital_option_trade(self, asset:str, amount:float, direction:str, expiry:int=1):
        """
        Execute a digital option trade with validation and error handling.
        
        Args:
            asset: Asset name to trade
            amount: Trade amount in dollars (minimum $1)
            direction: 'put' or 'call' trade direction
            expiry: Expiry time in minutes (default: 1)
            
        Returns:
            tuple: (success: bool, order_id: int or error_message: str)
        """

        try:
            direction = direction.lower()

            # Validate all parameters before execution
            self._validate_options_trading_parameters(asset, amount, direction, expiry)

            # Convert direction to API format
            direction_map = {'put': 'P', 'call': 'C'}        
            direction = direction_map[direction]

            # Generate unique request ID for tracking
            from random import randint
            request_id = str(randint(0, 100000))

            # Build message and send trade request
            msg = self._build_options_body(asset, amount, expiry, direction)
            self.ws_manager.send_message("sendMessage", msg, request_id)

            return self.wait_for_oreder_confirmation(request_id, expiry)
            
        except (InvalidTradeParametersError, TradeExecutionError, KeyError) as e:
                    logger.error(f"Trade execution failed: {e}")
        except Exception as e:
            # Catch any unexpected errors
            logger.error(f"Unexpected error during trade execution: {e}", exc_info=True)

    def wait_for_oreder_confirmation(self, request_id:int, expiry:int, timeout:int=10):
        """
        Wait for trade order confirmation from the server.
        
        Args:
            request_id: Unique request identifier to track
            timeout: Maximum wait time in seconds (default: 10)
            
        Returns:
            tuple: (success: bool, order_id: int or error_message: str)
        """
        start_time = time.time()
        
        # Poll for order confirmation within timeout
        while time.time() - start_time < timeout:
            result = self.message_handler.open_positions['digital_options'].get(request_id)
            if result is not None:
                if isinstance(result, int):
                    # Success: result is order ID
                    expires_in = get_remaining_secs(self.message_handler.server_time, expiry)
                    logger.info(f'Order Executed Successfully, Order ID: {result}, Expires in: {expires_in} Seconds')
                    return True, result
                else:
                    # Failure: result is error message
                    logger.error(f'Order Executed Failed, Reason: !!! {result} !!!')
                    return False, result
            time.sleep(0.1)
                
        logger.error(f"Order Confirmation timed out after {timeout} seconds")


    def _build_options_body(self, asset: str, amount: float, 
                           expiry: int, direction: str) -> str:
        """
        Build WebSocket message body for digital options trade.
        
        Args:
            asset: Asset name to trade
            amount: Trade amount in dollars
            expiry: Expiry time in minutes
            direction: Trade direction ('P' for put, 'C' for call)
            
        Returns:
            Formatted message dictionary for API
        """

        # Get asset ID and calculate expiration timestamp
        active_id = str(self.get_asset_id(asset))
        expiration = get_expiration(self.message_handler.server_time, expiry)
        date_formatted = datetime.fromtimestamp(expiration, UTC).strftime("%Y%m%d%H%M")

        # Build instrument ID following IQOption format
        instrument_id = f"do{active_id}A{date_formatted[:8]}D{date_formatted[8:]}00T{expiry}M{direction}SPT"

        return {
            "name": "digital-options.place-digital-option",
            "version": "3.0",
            "body": {
                "user_balance_id": int(self.account_manager.current_account_id),
                "instrument_id": str(instrument_id),
                "amount": str(amount),
                "asset_id": int(active_id),
                "instrument_index": 0,
                # "instrument_index": 83931
            }
        }
    
    def _validate_options_trading_parameters(self, asset: str, amount: float, direction: str, expiry: int) -> None:
        """
        Validate all trade parameters before order execution.
            
        Raises:
            InvalidTradeParametersError: If any parameter is invalid
            TradeExecutionError: If account is not available
        """

        # Validate asset name
        if not isinstance(asset, str) or not asset.strip():
            raise InvalidTradeParametersError("Asset name cannot be empty")
        
        # Validate trade amount (minimum $1)
        if not isinstance(amount, (int, float)) or amount < 1:
            raise InvalidTradeParametersError(f"Minimum Bet Amount is $1, got: {amount}")
        
        # Validate trade direction
        direction = direction.lower().strip()
        if direction not in ['put', 'call']:
            raise InvalidTradeParametersError(f"Direction must be 'put' or 'call', got: {direction}")
        
        # Validate expiry time
        if not isinstance(expiry, int) or expiry < 1:
            raise InvalidTradeParametersError(f"Expiry must be positive integer, got: {expiry}")
        
        # Ensure active account is available
        if not self.account_manager.current_account_id:
            raise TradeExecutionError("No active account available")
            

    def get_trade_outcome(self, order_id: int, expiry:int=1):
        """
        Monitor trade and return outcome when closed.
        
        Args:
            order_id: Order ID to monitor
            expiry: Original expiry time in minutes for timeout calculation
            
        Returns:
            tuple: (success: bool, pnl: float or None)
                success=True with PnL if trade closed, False if timeout
        """
        start_time = time.time()
        timeout = get_remaining_secs(self.message_handler.server_time, expiry)

        # Poll for trade closure with timeout + 3-second buffer
        while time.time() - start_time < timeout + 3:
            order_data = self.message_handler.position_info.get(order_id, {})

            # Check if trade is closed
            if order_data and order_data.get("status") == "closed":
                pnl = order_data.get('pnl', 0)
                result_type = "WIN" if pnl > 0 else "LOSS"
                logger.info(f"Trade closed - Order IDs: {order_id}, Result: {result_type}, PnL: ${pnl:.2f}")
                return True, pnl
            
            time.sleep(.5) # Check every 500ms

        # Trade did not close within expected timeframe
        return False, None