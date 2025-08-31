from datetime import datetime, UTC
import logging
import time

from options_assests import UNDERLYING_ASSESTS
from version2.utilities import get_expiration

logger = logging.getLogger(__name__)


# Custom exceptions for better error categorization
class TradeExecutionError(Exception):
    """Base exception for trade execution errors"""
    pass

class InvalidTradeParametersError(TradeExecutionError):
    """Raised when trade parameters are invalid"""
    pass


class TradeManager:
    def __init__(self, websocket_manager, message_handler, account_manager):
        self.ws_manager = websocket_manager
        self.message_handler = message_handler
        self.account_manager = account_manager

    def get_asset_id(self, asset_name: str) -> int:
        if asset_name in UNDERLYING_ASSESTS:
            return UNDERLYING_ASSESTS[asset_name]
        raise KeyError(f'{asset_name} not found!')

    def _execute_digital_option_trade(self, asset:str, amount:float, direction:str, expiry:int=1):
        """Place a digital option trade."""

        try:
            direction = direction.lower()
            self._validate_options_trading_parameters(asset, amount, direction, expiry)

            direction_map = {'put': 'P', 'call': 'C'}        
            direction = direction_map[direction]

            from random import randint
            request_id = str(randint(0, 100000))

            msg = self._build_options_body(asset, amount, expiry, direction)

            self.ws_manager.send_message("sendMessage", msg, request_id)

            return self.wait_for_oreder_confirmation(request_id)
            
        except (InvalidTradeParametersError, TradeExecutionError, KeyError) as e:
                    logger.error(f"Trade execution failed: {e}")
        except Exception as e:
            # Catch any unexpected errors
            logger.error(f"Unexpected error during trade execution: {e}", exc_info=True)

    def wait_for_oreder_confirmation(self, request_id:int, timeout:int=10):
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.message_handler.open_positions['digital_options'].get(request_id)
            if result is not None:
                if isinstance(result, int):
                    logger.info(f'Order Executed Successfully, Order ID: {result}')
                    return True, result
                else:
                    logger.error(f'Order Executed Failed, Reason: !!! {result} !!!')
                    return False, result
            time.sleep(0.1)
                
        logger.error(f"Order Confirmation timed out after {timeout} seconds")


    def _build_options_body(self, asset: str, amount: float, 
                           expiry: int, direction: str) -> str:
        active_id = str(self.get_asset_id(asset))
        expiration = get_expiration(self.message_handler.server_time, expiry)
        date_formatted = datetime.fromtimestamp(expiration, UTC).strftime("%Y%m%d%H%M")

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
            """Validate trade parameters before execution."""
            # Validate asset
            if not isinstance(asset, str) or not asset.strip():
                raise InvalidTradeParametersError("Asset name cannot be empty")
            
            # Validate amount
            if not isinstance(amount, (int, float)) or amount < 1:
                raise InvalidTradeParametersError(f"Minimum Bet Amount is $1, got: {amount}")
            
            # Validate direction
            direction = direction.lower().strip()
            if direction not in ['put', 'call']:
                raise InvalidTradeParametersError(f"Direction must be 'put' or 'call', got: {direction}")
            
            # Validate expiry
            if not isinstance(expiry, int) or expiry < 1:
                raise InvalidTradeParametersError(f"Expiry must be positive integer, got: {expiry}")
            
            if not self.account_manager.current_account_id:
                raise TradeExecutionError("No active account available")
