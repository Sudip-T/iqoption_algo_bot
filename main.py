import time
import json
import logging
from datetime import datetime
from version2.iqclient import IQOptionAlgoAPI

logger = logging.getLogger(__name__)


try:
    algobot = IQOptionAlgoAPI()
    algobot._connect()

except Exception as e:
    logger.error(e)
