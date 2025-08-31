import time
import json
import logging
from datetime import datetime
from version2.iqclient import IQOptionAlgoAPI

logger = logging.getLogger(__name__)


try:
    algobot = IQOptionAlgoAPI()
    algobot._connect()
    # algobot.websocket.start_websocket()

    algobot.execute_digital_option_trade('EURUSD-OTC', 1, 'CALL', 1)

except Exception as e:
    logger.error(e)
