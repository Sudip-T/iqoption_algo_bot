from enum import Enum
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Dict, Any


class OptionType(Enum):
    DIGITAL_OPTION = "digital-option"
    BINARY_OPTION = "binary-option"
    TURBO_OPTION = "turbo-option"

class Direction(Enum):
    PUT = "put"
    CALL = "call"

@dataclass
class OptionsTradeParams:
    """Trade parameters with validation"""
    asset: str
    expiry: int
    amount: float
    direction: Direction
    option_type: OptionType
    
    def __post_init__(self):
        if self.amount < 1:
            raise ValueError("Amount must be positive")
        if self.expiry < 1:
            raise ValueError("Expiry must be positive")