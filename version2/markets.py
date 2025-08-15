import time
import pandas as pd
import mplfinance as mpf
# from underlying_list import underlying_list
from typing import Optional, Dict, Any, List
from enum import Enum
import logging
from options_assests import UNDERLYING_ASSESTS


logger = logging.getLogger(__name__)


class InstrumentType(Enum):
    FOREX = 'forex'
    CFD = 'cfd'
    CRYPTO = 'crypto'
    DIGITAL_OPTION = 'digital-option'
    BINARY_OPTION = 'binary-option'

class MarketManager:
    def __init__(self, websocket_manager, message_handler):
        self.ws_manager = websocket_manager
        self.message_handler = message_handler
    
    def get_asset_id(self, asset_name: str) -> int:
        if asset_name in UNDERLYING_ASSESTS:
            return UNDERLYING_ASSESTS[asset_name]
        raise KeyError(f'{asset_name} not found!')
    
    def get_candle_history(self, asset_name: str, count: int = 50, timeframe: int = 60):
        """
        Get historical candle data for an asset
        
        Args:
            asset_name: Name of the trading asset
            count: Number of candles to retrieve
            timeframe: Timeframe of each candle in seconds
        """

        self.message_handler.candles = None
        
        name = "sendMessage"
        msg = {
            "name": "get-candles",
            "version": "2.0",
            "body": {
                "active_id": self.get_asset_id(asset_name),
                "size": timeframe,
                "count": count,
                "to": self.message_handler.server_time,
                "only_closed": True,
                "split_normalization": True
            }
        }
        
        self.ws_manager.send_message(name, msg)
        
        while self.message_handler.candles is None:
            time.sleep(0.1)
        
        return self.message_handler.candles
    
    def plot_candles(self, candles_data=None):
        if candles_data is None:
            candles_data = self.message_handler.candles
        
        if not candles_data:
            print("No candle data available")
            return
        
        df = pd.DataFrame(candles_data)
        df = df.rename(columns={
            'open': 'Open',
            'max': 'High',
            'min': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        })
        
        df['timestamp'] = pd.to_datetime(df['from'], unit='s')
        df = df.set_index('timestamp')
        
        mpf.plot(
            df,
            type='candle',
            style='charles',
            title='IQOption Candles',
            ylabel='Price',
            volume=False
        )
    
    def save_candles_to_csv(self, candles_data=None, filename: str = 'candles'):
        if candles_data is None:
            candles_data = self.message_handler.candles
        
        if not candles_data:
            print("No candle data to save")
            return
        
        df = pd.DataFrame(candles_data)
        df = df.rename(columns={'max': 'high','min': 'low'})

        df['from'] = pd.to_datetime(df['from'], unit='s')
        df['to'] = pd.to_datetime(df['to'], unit='s')
        
        df.to_csv(f'{filename}.csv', index=False)

    def _build_msg_body(self, instrument_type:str):
        if instrument_type == 'digital-option':
            msg = {
                "name": "digital-option-instruments.get-underlying-list",
                "version": "3.0",
                "body": {
                    "filter_suspended": True
                }
            }
        elif instrument_type == 'binary-option':
            msg= {
                'body':{},
                'name':'get-initialization-data',
                'version':'4.0'
            }
        elif instrument_type in ['forex', 'cfd', 'crypto']:
            msg = {
                'body':{},
                'version':'1.0',
                'name':f'marginal-{instrument_type}-instruments.get-underlying-list'
            }

        return msg
    
    def get_underlying_assests(self, instrument_type:str):
        # Validate instrument_type ['forex'/'cfd'/'crypto'/'digital-option'/'binary-option']
        valid_types = {instrument.value for instrument in InstrumentType}
        if instrument_type not in valid_types:
            raise ValueError(f"Unsupported instrument type: {instrument_type}. "
                           f"Must be one of: {', '.join(valid_types)}")

        # reset state
        self.message_handler._underlying_assests = None

        self.ws_manager.send_message('sendMessage', self._build_msg_body(instrument_type))

        while self.message_handler._underlying_assests == None:
            time.sleep(.1)

        return self.message_handler._underlying_assests


    def save_underlying_assests_to_file(self):
        options_underlying_assets = {}
        marginal_underlying_assets = {}

        for instrument in ['forex', 'cfd', 'crypto']:
            underlying_list = self.get_underlying_assests(instrument)
            for item in underlying_list:
                if item['is_suspended'] == False:
                    marginal_underlying_assets[item['name']] = item['active_id']

        digital_underlying = self.get_underlying_assests('digital-option')
        initialization_data = self.get_underlying_assests('binary-option')

        for assest in digital_underlying:
            if assest['is_suspended'] == False:
                options_underlying_assets[assest['name']] = assest['active_id']

        instruments = ['binary', 'blitz', 'turbo']
        for instrument in instruments:
            if instrument in initialization_data:
                for _, value  in initialization_data[instrument]['actives'].items():
                    if value['is_suspended'] == False:
                        options_underlying_assets[value['ticker']] = value['id']

        self._export_assets_to_fiel(options_underlying_assets, 'options_assests.py')
        self._export_assets_to_fiel(marginal_underlying_assets, 'marginal_assests.py')

    def _export_assets_to_fiel(self, data:dict, file:str) -> None:
        with open(f'{file}', 'w') as file:
            file.write('#Auto-Generated Underlying List\n')
            file.write('UNDERLYING_ASSESTS = {\n')
            for key,value in data.items():
                file.write(f"   '{key}':{value},\n")
            file.write('}\n')