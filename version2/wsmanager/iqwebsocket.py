import json
import time
import threading
import websocket
import logging

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self, ws_url, message_handler):
        self.ws_url = ws_url
        self.websocket = None
        self.ws_is_active = False
        self.message_handler = message_handler
        
    def start_websocket(self):
        self.websocket = websocket.WebSocketApp(
            self.ws_url,
            on_message=self._on_message,
            on_open=self._on_open,
            on_close=self._on_close,
            on_error=self._on_error
        )
        
        wst = threading.Thread(target=self.websocket.run_forever)
        wst.daemon = True
        wst.start()
        
        while not self.ws_is_active:
            time.sleep(0.1)
    
    def send_message(self, name, msg, request_id=""):
        if request_id == '':
            request_id = int(str(time.time()).split('.')[1])
        
        data = json.dumps(dict(
            name=name,
            msg=msg,
            request_id=request_id
        ))
        
        self.websocket.send(data)
        return request_id
    
    def _on_message(self, ws, message):
        print(message, '\n')
        try:
            message = json.loads(message)
            self.message_handler.handle_message(message)
            self.ws_is_active = True
        except json.JSONDecodeError as e:
            print(f"Error parsing message: {e}")
    
    def _on_error(self, ws, error):
        print(f"### WebSocket Error: {error} ###")
    
    def _on_open(self, ws):
        print("### WebSocket opened ###")
    
    def _on_close(self, ws, close_status_code, close_msg):
        print("### WebSocket closed ###")
    
    def close(self):
        if self.websocket:
            self.websocket.close()