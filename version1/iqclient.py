import os
import time
import json
import requests
import websocket
import threading
import operator

import pandas as pd
import mplfinance as mpf

from version1.underlying_list import underlying_list

from dotenv import load_dotenv
load_dotenv()


class IQOptionAPI:
    login_url = 'https://api.iqoption.com/v2/login'
    logout_url = "https://auth.iqoption.com/api/v1.0/logout"
    ws_url = 'wss://ws.iqoption.com/echo/websocket'

    def __init__(self, email=os.getenv('email'), password=os.getenv('password')):
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.websocket = None
        self.ws_is_active = False
        self.profile_msg = None
        self.balance_data = None
        self.active_balance_id = None
        self.underlying_list = None
        self.initialization_data = None

        self.candles = None
        self.server_time = None

    def login(self):
        data = {
            'identifier': self.email,
            'password': self.password
        }
        response = self.session.post(url=self.login_url, data=data)
        response.raise_for_status()
        print('\n[✓] Successfully logged in to IQ Option\n')
        self.start_websocket()
        return response

    def logout(self, data=None):
        return self.session.post(url=self.logout_url, data=data)

    def start_websocket(self):
        self.websocket = websocket.WebSocketApp(
            self.ws_url, 
            on_message=self.on_message, 
            on_open=self.on_open, 
            on_close=self.on_close, 
            on_error=self.on_error
        )

        wst = threading.Thread(target=self.websocket.run_forever)
        wst.daemon = True
        wst.start()

        while self.ws_is_active == False:
            time.sleep(0.1)

        ssid = self.session.cookies.get('ssid')
        name = 'ssid'
        data = json.dumps(dict(name=name, msg=ssid))
        self.websocket.send(data)

        self.send_websocket_request(name, ssid)
        
        while self.profile_msg is None:
            time.sleep(1)

    def send_websocket_request(self, name, msg, request_id=""):
        if request_id == '':
            request_id = int(str(time.time()).split('.')[1])

        data = json.dumps(dict(
            name=name,
            msg=msg, 
            request_id=request_id
        ))
        self.websocket.send(data)

    def fetch_account_balances(self):
        self.balance_data = None
        name = 'sendMessage'
        data = {
            'name': 'get-balances',
            'version': '1.0'
        }
        self.send_websocket_request(name, data)

        while self.balance_data == None:
            time.sleep(.1)

        return self.balance_data

    def fetch_account_balances_v2(self):
        self.balance_data = None
        data = {
                "name": "sendMessage",
                "request_id": "",
                # "local_time": "16643",
                "msg": {
                    "name": "internal-billing.get-balances",
                    "version": "1.0",
                    "body": {
                    "types_ids": [1, 4, 2, 6],
                    "tournaments_statuses_ids": [3, 2]
                    }
                }
            }

        self.websocket.send(json.dumps(data))
        
        while self.balance_data == None:
            time.sleep(.1)

        return self.balance_data

    def get_tournaments_accounts(self) -> list:
        self.fetch_account_balances_v2()
        while self.balance_data is None:
            time.sleep(0.2)

        tournaments_accounts = []
        for item in self.balance_data:
            if item['type'] == 2:
                tournaments_accounts.append({
                    'id': item['id'], 
                    'name': item['tournament_name'],  
                    'balance': item['amount']
                })
        return tournaments_accounts
    

    def on_message(self, ws, message):
        # print(message)
        message = json.loads(message)
        self.ws_is_active = True

        if message['name'] == 'server_time':
            self.server_time = message['msg']

        elif message['name'] == 'profile':
            self.profile_msg = message

            balances = message['msg']['balances']
            for balance in balances:
                if balance['type'] == 4:
                    self.active_balance_id = balance['id']
                    break

            with open('profile.json', 'w') as file:
                json.dump(message, file, indent=4)

        elif message['name'] == 'balances':
            self.balance_data = message['msg']
            with open('balances.json', 'w') as file:
                json.dump(message, file, indent=4)

        elif message['name'] == 'training-balance-reset':
            print(message)

        elif message['name'] == 'initialization-data':
            self.initialization_data = message['msg']

        elif message['name'] == 'candles':
            self.candles = message['msg']['candles']

        elif message['name'] == 'underlying-list':
            if message['msg'].get('type', None) == 'digital-option':
                self.underlying_list = message['msg']['underlying']
            else:
                self.underlying_list = message['msg']['items']


    def on_error(self, ws, error):
        print(f"### Error! : {error} ###")

    def on_open(self, ws):
        print("### WebSocket opened ###")

    def on_close(self, ws, close_status_code, close_msg):
        print("### WebSocket closed ###")


    def get_active_account_balance(self):
        accounts = self.fetch_account_balances_v2()

        for account in accounts:
            if account['id'] == self.active_balance_id:
                return account['amount']
                break

    def switch_account(self, account_type:str):
        if account_type.lower() not in ['real', 'demo']:
            print('invalid account type')
            return
        
        accounts = self.fetch_account_balances_v2()

        real_account_id = None
        demo_account_id = None

        for account in accounts:
            if account['type'] == 1:
                real_account_id = account['id']
            if account['type'] == 4:
                demo_account_id = account['id']

        print(real_account_id, demo_account_id)

        if account_type.lower() == 'real':
            self.stage_active_account(real_account_id)
        elif account_type.lower() == 'demo':
            self.stage_active_account(demo_account_id)

    def stage_active_account(self, account_id):
        if self.active_balance_id != None:
            self.portfolio_position_change('unsubscribeMessage', self.active_balance_id)

        self.active_balance_id = account_id

        self.portfolio_position_change('subscribeMessage', self.active_balance_id)


    def portfolio_position_change(self, msg_name, account_id):
        instrument_types = ['cfd', 'forex', 'crypto', 'digital-option', 'binary-option']
        for instrument in instrument_types:
            msg={"name": 'portfolio.position-changed',
            "version": "2.0",
            "params": {
                "routingFilters": {"instrument_type": str(instrument),
                "user_balance_id":account_id    
                            
                    }
                }
            }

        self.send_websocket_request(msg_name, msg)


    def refill_demo_balance_v2(self):
        name = 'sendMessage'
        msg = {
            'name':'reset-training-balance',
            'version':'2.0'
        }

        self.send_websocket_request(name, msg)

    def refill_demo_balance_v4(self):
        name = 'sendMessage'
        msg = {
            'name':'internal-billing.reset-training-balance',
            'version':'4.0',
            'body':{
                'amount': int(input('Enter Amount to Refill: ')),
                'user_balance_id':self.profile_msg['msg']['balances'][-1]['id']
            }
        }

        self.send_websocket_request(name, msg)


    def get_digital_underlying_list(self):
        self.underlying_list = None

        name = "sendMessage"
        msg = {
            "name": "digital-option-instruments.get-underlying-list",
            "version": "3.0",
            "body": {
                "filter_suspended": True
            }
        }

        self.send_websocket_request(name, msg)

        while self.underlying_list == None:
            time.sleep(.1)

        return self.underlying_list

        
        with open('underlying_list.py', 'w') as file:
            file.write('#My Auto-Generated Underlying List\n')
            file.write('underlying_list = {\n')
            for item in self.underlying_list:
                file.write(f"   '{item['name']}':{item['active_id']},\n")
            file.write('}\n')

        # for item in self.underlying_list:
        #     active_id = item['active_id']
        #     name = item['name']
        #     print('Assest id: ', active_id, 'Name: ', name)

    def get_marginal_underlying_list(self, instrument:str) -> list:
        self.underlying_list = None

        name = 'sendMessage'
        msg = {
            'body':{},
            'version':'1.0',
            'name':f'marginal-{instrument}-instruments.get-underlying-list'
        }

        self.send_websocket_request(name, msg)

        while self.underlying_list == None:
            time.sleep(.5)

        return self.underlying_list

    def write_underlying_assest_to_file(self, instruments:list) -> None:
        # instruments=['forex', 'cfd', 'crypto']

        mergerd_underlying_list = list()

        for instrument in instruments:
            underlying_list = self.get_marginal_underlying_list(instrument)
            mergerd_underlying_list.extend(underlying_list)

        with open('marginal_underlying_list.py', 'w') as file:
            file.write('#My Auto-Generated Underlying List\n')
            file.write('ASSESTS = {\n')
            for item in mergerd_underlying_list:
                if item['is_suspended'] == False:
                    file.write(f"   '{item['name']}':{item['active_id']},\n")
            file.write('}\n')


    def get_initialization_data(self):
        self.initialization_data = None

        name = 'sendMessage'
        msg = {
            'body':{},
            'name':'get-initialization-data',
            'version':'4.0'
        }

        self.send_websocket_request(name, msg)

        while self.initialization_data == None:
            time.sleep(.1)

        assets = {}
        instruments = ['binary', 'blitz', 'turbo']
        for instrument in instruments:
            if instrument in self.initialization_data:
                for _, value in self.initialization_data[instrument]['actives'].items():
                    if value['is_suspended'] == False:
                        assets[value['ticker']] = value['id']

        with open('test_today.py', 'w') as file:
            file.write('#My Auto-Generated Underlying List\n')
            file.write('ASSESTS = {\n')
            for key, value in assets.items():
                file.write(f"   '{key}':{value},\n")
            file.write('}\n')

    def get_asset_id(self, asset_name:str) -> int:
        if asset_name in underlying_list:
            return underlying_list[asset_name]
        raise KeyError(f'{asset_name} not found!')

    def get_candle_history(self, asset_name:str='EURUSD-op', count:int=50, timeframe:int=60):
        """
        Args:
        asset_name (str, optional): Name of the trading asset ('EURUSD-op', 'USDJPY-OTC',...). Defaults to 'EURUSD-op'
        count (int, optional): Number of candles to retrieve. Defaults to 50
        size (int, optional): Timeframe of each candle in seconds (e.g., 60 = 1-minute candles). Defaults to 60
        """

        name = "sendMessage"
        msg = {
        "name": "get-candles",
        "version": "2.0",
        "body": {
            "active_id": self.get_asset_id(asset_name),
            "size": timeframe,
            "count":count,
            "to": self.server_time,
            "only_closed": True,
            "split_normalization": True
        }
    }
        
        self.send_websocket_request(name, msg)

        while self.candles == None:
            time.sleep(.1)


    def plot_candles(self, candles_data) -> None:
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
            volume=False  # Set to True if you want volume bars
        )

    def save_candles_to_csv(self, candles_data, filename:str='candles'):
        df = pd.DataFrame(candles_data)
        df = df.rename(columns={
            'max':'high',
            'min':'low',
        })
        df['from'] = pd.to_datetime(df['from'], unit='s')
        df['to'] = pd.to_datetime(df['to'], unit='s')
        df.to_csv(f'{filename}.csv', index=False)



api = IQOptionAPI()
api.login()


asset = 'EURUSD-op'
candles_count = 20
timeframe = 60


api.get_candle_history(asset_name=asset, count=candles_count, timeframe=timeframe)
api.save_candles_to_csv(api.candles, filename=asset)
api.plot_candles(api.candles)




# api.switch_account('real')
# print('real account balance: ', api.get_active_account_balance())

# api.switch_account('demo')
# print('Demo account balance: ', api.get_active_account_balance())



