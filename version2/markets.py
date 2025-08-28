import time
import pandas as pd
import mplfinance as mpf
# from underlying_list import underlying_list
from typing import Optional, Dict, Any, List
from enum import Enum
import logging
from options_assests import UNDERLYING_ASSESTS


logger = logging.getLogger(__name__)


from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
import threading

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


        self.live_plot_active = False
        self.plot_thread = None
        self.plot_timeout = None
        self.current_timeframe = None
        self.tick_data = pd.DataFrame(columns=['Price', 'Volume'])
        self.tick_data.index = pd.DatetimeIndex([])
        self.candles = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
        self.candles.index = pd.DatetimeIndex([])
        self.last_candle_time = None
        self.lock = threading.Lock()
        self.fig = None
        self.axes = None
    
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
        data = dict(sorted(data.items(), key=lambda item:item[-1]))
        with open(f'{file}', 'w') as file:
            file.write('#Auto-Generated Underlying List\n')
            file.write('UNDERLYING_ASSESTS = {\n')
            for key,value in data.items():
                file.write(f"   '{key}':{value},\n")
            file.write('}\n')

    # def subscribe_candles(self, asset_name:str, timeframe:int=60) -> None:
    #     """Subscribe to candle data for an asset"""
    #     # Subscribe to real-time candles
    #     self.ws_manager.send_message('subscribeMessage', {
    #         'name': 'candle-generated',
    #         'params': {
    #             'routingFilters': {
    #                 'active_id': self.get_asset_id(asset_name),
    #                 'size': timeframe
    #             }
    #         }
    #     })


    def subscribe_candles(self, asset_name: str, timeframe: int = 60, plot_timeout: int = None):
        """Subscribe to candle data and start live plotting with proper timeframe aggregation"""
        # Stop any existing plot
        self.stop_live_plot()
        
        # Reset data structures
        with self.lock:
            self.tick_data = pd.DataFrame(columns=['Price', 'Volume'])
            self.tick_data.index = pd.DatetimeIndex([])
            self.candles = pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
            self.candles.index = pd.DatetimeIndex([])
            self.last_candle_time = None
            self.current_timeframe = timeframe
        
        # Subscribe to candle data
        self.ws_manager.send_message('subscribeMessage', {
            'name': 'candle-generated',
            'params': {
                'routingFilters': {
                    'active_id': self.get_asset_id(asset_name),
                    'size': timeframe
                }
            }
        })
        
        # # Set up live plotting
        # self.live_plot_active = True
        # self.plot_timeout = plot_timeout
        # self.plot_thread = threading.Thread(target=self._run_live_plot)
        # self.plot_thread.daemon = True
        # self.plot_thread.start()
    
    def stop_live_plot(self):
        """Stop the live plotting"""
        self.live_plot_active = False
        if self.plot_thread and self.plot_thread.is_alive():
            self.plot_thread.join()
        if self.fig:
            plt.close(self.fig)
    
    def _process_tick(self, tick):
        """Process incoming tick data and aggregate into timeframe candles"""
        if not tick or 'ask' not in tick or 'bid' not in tick:
            return
            
        try:
            # Convert timestamp to pandas Timestamp for floor operation
            timestamp = pd.to_datetime(tick['at'], unit='ns')
            price = (tick['ask'] + tick['bid']) / 2  # Mid price
            volume = tick.get('volume', 0)
            
            with self.lock:
                # Add tick to DataFrame
                new_tick = pd.DataFrame([{
                    'Price': price,
                    'Volume': volume
                }], index=[timestamp])
                self.tick_data = pd.concat([self.tick_data, new_tick])
                
                # Determine current candle time using pandas floor
                candle_time = timestamp.floor(f'{self.current_timeframe}s')
                
                # If new candle period starts
                if self.last_candle_time is None or candle_time > self.last_candle_time:
                    # Finalize previous candle if exists
                    if self.last_candle_time is not None:
                        period_ticks = self.tick_data.loc[self.last_candle_time:candle_time - timedelta(microseconds=1)]
                        if not period_ticks.empty:
                            new_candle = pd.DataFrame([{
                                'Open': period_ticks['Price'].iloc[0],
                                'High': period_ticks['Price'].max(),
                                'Low': period_ticks['Price'].min(),
                                'Close': period_ticks['Price'].iloc[-1],
                                'Volume': period_ticks['Volume'].sum()
                            }], index=[self.last_candle_time])
                            self.candles = pd.concat([self.candles, new_candle])
                    
                    # Start new candle
                    self.last_candle_time = candle_time
                    
                    # Keep only ticks from current candle period for memory efficiency
                    self.tick_data = self.tick_data.loc[self.last_candle_time:]
        except Exception as e:
            print(f"Error processing tick: {e}")
    
    def _run_live_plot(self):
        """Background thread for live plotting"""
        start_time = time.time()
        
        # Wait for some initial data before creating the plot
        while self.live_plot_active and self.candles.empty:
            tick = self.message_handler.get_latest_tick()
            if tick:
                self._process_tick(tick)
            time.sleep(0.1)
        
        if not self.live_plot_active:
            return
        
        # Create initial dummy data with proper DatetimeIndex for the plot
        current_time = datetime.now()
        dummy_data = pd.DataFrame({
            'Open': [1.0],
            'High': [1.0],
            'Low': [1.0], 
            'Close': [1.0],
            'Volume': [0]
        }, index=pd.DatetimeIndex([current_time]))
        
        try:
            # Create figure with dummy data
            self.fig, self.axes = mpf.plot(
                dummy_data,
                type='candle',
                volume=True,
                returnfig=True,
                style='charles',
                figratio=(12, 8),
                figscale=1.0
            )
            plt.ion()
            plt.show()
            
            while self.live_plot_active:
                # Check timeout
                if self.plot_timeout and (time.time() - start_time) > self.plot_timeout:
                    self.live_plot_active = False
                    break
                
                # Get latest tick from message handler
                tick = self.message_handler.get_latest_tick()
                if tick:
                    self._process_tick(tick)
                    
                    # Update plot if we have candles
                    with self.lock:
                        if not self.candles.empty:
                            for ax in self.axes:
                                ax.clear()
                            
                            # Plot complete candles
                            mpf.plot(
                                self.candles,
                                type='candle',
                                ax=self.axes[0],
                                volume=self.axes[1],
                                style='charles',
                                datetime_format='%H:%M',
                                axtitle=f'Live {self.current_timeframe}s Candles (Last: {self.candles["Close"].iloc[-1]:.5f})',
                                update_width_config=dict(
                                    candle_linewidth=1.0,
                                    candle_width=0.8
                                )
                            )
                            
                            # If we have partial candle data, plot it differently
                            if not self.tick_data.empty and self.last_candle_time is not None:
                                current_open = self.tick_data['Price'].iloc[0]
                                current_high = self.tick_data['Price'].max()
                                current_low = self.tick_data['Price'].min()
                                current_close = self.tick_data['Price'].iloc[-1]
                                current_volume = self.tick_data['Volume'].sum()
                                
                                # Draw partial candle
                                self.axes[0].plot([self.last_candle_time], [current_open], 'bo')
                                self.axes[0].vlines(
                                    x=self.last_candle_time,
                                    ymin=current_low,
                                    ymax=current_high,
                                    colors='b',
                                    linewidth=1
                                )
                                self.axes[0].plot(
                                    [self.last_candle_time, self.last_candle_time + timedelta(seconds=self.current_timeframe)],
                                    [current_close, current_close],
                                    'b-'
                                )
                            
                            plt.pause(0.01)
                
                time.sleep(0.05)  # Prevent high CPU usage
        except Exception as e:
            print(f"Error in plotting thread: {e}")
        finally:
            if self.fig:
                plt.close(self.fig)