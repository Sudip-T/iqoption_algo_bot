"""
Main trading script demonstrating comprehensive usage of the IQOption API.

This script showcases all available API methods including:
- Account management (login, balance, switching accounts)
- Market data retrieval and export
- Position history analysis
- Digital options trading
- Trade outcome tracking

Author: Sudip Thapa (TG - Code2AutomatewithSudip)
"""


import time
import logging
from datetime import datetime, timedelta
from version2.iqclient import *

# Configure logging for better output visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    "Main function demonstrating complete IQOption API usage"

    print_developer_info()
    
    print("\n📡 Initializing API and Establishing Connection")
    print("-" * 50)
    
    aibot = IQOptionAlgoAPI()
    
    # Establish full connection (login + websocket + authentication)
    aibot._connect()
    
    # try:
    #     print("\n💰 Account Management Operations including Account Switching")
    #     print("-" * 63)

    #     # Get current account balance
    #     print(f"💵 Current Account Balance: ${aibot.get_current_account_balance():.2f}")
        
    #     # Display available tournament accounts
    #     print("🏆 Checking Tournament Accounts...")
    #     tournament_accounts = aibot.get_tournament_accounts()
    #     if tournament_accounts:
    #         logger.info(f"📋 Found {len(tournament_accounts)} tournament accounts:")
    #         for acc in tournament_accounts[:3]:  # Show first 3
    #             logger.info(f"   - {acc.get('name', 'Unknown')} (Balance: ${acc.get('balance', 0):.2f})")
    #     else:
    #         print(" No tournament accounts available")
        
    #     print("🔄 Testing Account Switch...")
    #     aibot.switch_account("real")  # Switch to real account    

    #     print("💰 Refilling Demo Account...")
    #     aibot.refill_demo_account()  # defaults to $10,000
            
    # except Exception as e:
    #     print(f"❌ Account management error: {e}")
    

    # # ========================================
    # # 3. MARKET DATA OPERATIONS
    # # ========================================
    
    # print("\n💰 Market Data Operations including Underlying Assets Fetching")
    # print("-" * 63)
    
    # try:
    #     aibot.get_candle_history('EURUSD-OTC', 20, 3000)

    #     csv_filename = f"{asset}_candle"
    #     save_result = aibot.save_candles_to_csv(candles, csv_filename)
    
    # except Exception as e:
    #     print(f"❌ Market data error: {e}")


    # print("\n💰 Place Digital Options Trade and Check the Outcome")
    # print("-" * 55)

    # status, result = aibot.execute_digital_option_trade('EURUSD-OTC', 1, 'CALL', 1)
    # if status:
    #     result = aibot.get_trade_outcome(result, 1)

    print("\n💰 Place Binary Options Trade and Check the Outcome")
    print("-" * 55)

    status, result = aibot.execute_options_trade(OptionsTradeParams(
                        asset="EURUSD-op",
                        amount=1,
                        direction=Direction.CALL,
                        option_type=OptionType.DIGITAL_OPTION,
                        expiry=1,
                    ))

    if status:
        is_closed, data = aibot.get_trade_outcome(result, 1)

def print_footer():
    """Display footer information"""
    print("\n" + "=" * 75)
    print("📈 Thank you for using IQOption Royal Trading Bot")
    print("💡 For support or custom development, contact: @Code2AutomatewithSudip")
    print("=" * 75)


def print_developer_info():
    """Display developer and proprietary information"""
    print("=" * 73)
    print("🤖 IQOption Royal - Advanced IQOption Trading Bot Powered By Python 2.0")
    print("=" * 73)
    print()
    print("🔧 DEVELOPER INFORMATION")
    print("-" * 30)
    print("👨‍💻 Developer: Sudip Thapa")
    print("📱 Telegram: @Code2AutomatewithSudip")
    print("🌐 Contact: myselfsudipthapa1994@gmail.com")
    print()
    # print("⚡ FEATURES")
    # print("-" * 15)
    # print("✅ Real-time Market Data Processing")
    # print("✅ Advanced Risk Management")
    # print("✅ Multi-Account Support")
    # print("✅ Automated Trade Execution")
    # print("✅ Comprehensive Logging & Analytics")
    print("=" * 70)


if __name__ == "__main__":    
    try:
        main()
        print_footer()
    except KeyboardInterrupt:
        print("\n\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        logger.error(f"Demo execution error: {e}")
