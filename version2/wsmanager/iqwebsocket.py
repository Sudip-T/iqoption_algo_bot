import json
import time
import logging
import websocket
import threading
from version2.settings import WS_URL

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manages WebSocket connections for real-time communication with IQ Option.
    
    This class handles the WebSocket lifecycle including connection establishment,
    message sending/receiving, error handling, and connection cleanup. It uses
    a separate thread for the WebSocket connection to avoid blocking the main thread.
    """
    def __init__(self, message_handler):
        """
        Initialize the WebSocket manager with message handler.
        
        Args:
            message_handler: Handler instance that processes incoming messages
        """
        self.ws_url = WS_URL
        self.websocket = None
        self.ws_is_active = False
        self.message_handler = message_handler
        
    def start_websocket(self):
        """
        Initialize and start the WebSocket connection in a separate daemon thread.
        
        Creates a WebSocketApp instance with event handlers and starts it in a
        daemon thread to prevent blocking. Waits for connection to be established
        before returning.
        """

        # Create WebSocket application with event handlers
        self.websocket = websocket.WebSocketApp(
            self.ws_url,
            on_message=self._on_message,  # Handle incoming messages
            on_open=self._on_open,        # Handle connection opened
            on_close=self._on_close,      # Handle connection closed
            on_error=self._on_error       # Handle connection errors
        )
        
        # Start WebSocket in a daemon thread (dies when main thread exits)
        wst = threading.Thread(target=self.websocket.run_forever)
        wst.daemon = True
        wst.start()
        
        # Wait for connection to be established before proceeding
        while not self.ws_is_active:
            time.sleep(0.1)
    
    def send_message(self, name, msg, request_id=""):
        """
        Send a message through the WebSocket connection.
        
        Constructs a JSON message with name, msg, and request_id fields.
        If no request_id is provided, generates one using current timestamp.
        
        Args:
            name (str): Message type/name identifier
            msg (dict): Message payload data
            request_id (str, optional): Unique request identifier. 
                                      Auto-generated if not provided.
        
        Returns:
            str: The request_id used for this message (useful for tracking responses)
        """

        # Generate request ID from timestamp microseconds if not provided
        if request_id == '':
            request_id = int(str(time.time()).split('.')[1])
        
        # Construct message data structure
        data = json.dumps(dict(name=name, msg=msg, request_id=request_id))
        
        self.websocket.send(data)
        return request_id
    
    def _on_message(self, ws, message):
        """
        Handle incoming WebSocket messages.
        
        Parses JSON messages and forwards them to the message handler.
        Sets the connection as active upon receiving the first valid message.
        
        Args:
            ws: WebSocket instance (unused but required by websocket-client)
            message (str): Raw message data received from WebSocket
        """
        # print(message, '\n')
        try:
            message = json.loads(message) # Parse JSON message
            self.message_handler.handle_message(message) # Forward to message handler for processing
            self.ws_is_active = True # Mark connection as active after successful message processing
        except json.JSONDecodeError as e:
            print(f"Error parsing message: {e}")
    
    def _on_error(self, ws, error):
        """
        Handle WebSocket connection errors.
        
        Args:
            ws: WebSocket instance (unused but required by websocket-client)
            error: Error information from the WebSocket connection
        """
        print(f"### WebSocket Error: {error} ###")
        # Note: Could add more sophisticated error handling here such as:
        # - Logging with proper log levels
        # - Reconnection logic
        # - Error categorization and specific responses
    
    def _on_open(self, ws):
        """
        Handle WebSocket connection opened event.
        
        Called when the WebSocket connection is successfully established.
        
        Args:
            ws: WebSocket instance (unused but required by websocket-client)
        """
        # print("### WebSocket opened ###")
        pass
    
    def _on_close(self, ws, close_status_code, close_msg):
        """
        Handle WebSocket connection closed event.
        
        Called when the WebSocket connection is closed, either intentionally
        or due to network issues.
        
        Args:
            ws: WebSocket instance (unused but required by websocket-client)
            close_status_code: WebSocket close status code
            close_msg: Close message/reason
        """
        print("### WebSocket closed ###")
    
    def close(self):
        """
        Gracefully close the WebSocket connection.
        
        Closes the WebSocket connection if it exists and resets the connection status.
        Should be called when shutting down the application or switching connections.
        """
        if self.websocket:
            self.websocket.close()