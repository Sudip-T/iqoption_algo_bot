import time
from version2.iqclient import IQOptionAlgoAPI


try:
    algobot = IQOptionAlgoAPI()
    algobot._connect()

    algobot.save_underlying_assests_to_file()

    # # time.sleep(1)
    candles = algobot.market_manager.get_candle_history('EURUSD-OTC')
    algobot.market_manager.plot_candles(candles)


    # algobot.switch_account('demo')
except Exception as e:
    print(e)
