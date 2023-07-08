import alpaca_trade_api as tradeapi
import yfinance as yf
import pandas as pd
from talib import MACD, RSI, BBANDS
from datetime import datetime, timedelta
import backtrader as bt
import os
import logging
import pytz
import time
import sys

# Initialize the Alpaca API
APIKEYID = os.getenv('APCA_API_KEY_ID')
APISECRETKEY = os.getenv('APCA_API_SECRET_KEY')
APIBASEURL = os.getenv('APCA_API_BASE_URL')
api = tradeapi.REST(APIKEYID, APISECRETKEY, APIBASEURL)

current_time_zone = datetime.now(pytz.timezone('America/New_York'))

current_time = datetime.now(pytz.timezone('America/New_York')).strftime("%A, %b-%d-%Y %H:%M:%S")

# Set up logging
logging.basicConfig(filename='stock_bot.log', level=logging.INFO, format='%(asctime)s %(message)s')


# Load stock symbols from a text file
def load_symbols(filename):
    symbols = []
    try:
        with open(filename, 'r') as file:
            symbols = [line.strip() for line in file.readlines()]
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
    return symbols


# Stock symbols to monitor
SYMBOLS = load_symbols('successful-stocks-list.txt')


def get_current_time_zone():
    current_time_zone = datetime.now(pytz.timezone('America/New_York'))
    return current_time_zone


def get_current_time():
    current_time = datetime.now(pytz.timezone('America/New_York')).strftime("%A, %b-%d-%Y %H:%M:%S")
    return current_time


def print_account_info():
    # Get account details
    account = api.get_account()

    # Print account information
    print("\nAccount Information:")
    print(f"{(current_time)}" )
    print(f"Day Trade Count: {account.daytrade_count} out of 3 total Day Trades in 5 business days.")
    print(f"Current Account Cash: ${float(account.cash):.2f}")
    print("--------------------")

    # Log account information
    logging.info("\nAccount Information:")
    logging.info(f"{get_current_time()}")
    logging.info(f"Day Trade Count: {account.daytrade_count} out of 3 total Day Trades in 5 business days.")
    logging.info(f"Current Account Cash: ${float(account.cash):.2f}")
    logging.info("--------------------")


def print_positions():
    # Get current positions
    positions = api.list_positions()

    # Print current positions
    print("\nCurrent Positions:")
    for position in positions:
        symbol = position.symbol
        current_price = float(position.current_price)
        closing_price = float(position.prev_close_price)
        print(f"Symbol: {symbol}, Current Price: ${current_price:.2f}, Yesterday's Closing Price: ${closing_price:.2f}")
    print("--------------------")

    # Log current positions
    logging.info("\nCurrent Positions:")
    for position in positions:
        symbol = position.symbol
        current_price = float(position.current_price)
        closing_price = float(position.prev_close_price)
        logging.info(
            f"Symbol: {symbol}, Current Price: ${current_price:.2f}, Yesterday's Closing Price: ${closing_price:.2f}")
    logging.info("--------------------")


class MyStrategy(bt.Strategy):
    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=14)
        self.macd = bt.indicators.MACD(self.data.close)
        self.bbands = bt.indicators.BollingerBands(self.data.close)

    def next(self):
        if not self.position:
            # Buy condition
            if self.data.close[0] > self.data.close[-1] * 1.09 and self.rsi < 30 and self.macd.macd > self.macd.signal and self.data.close < self.bbands.lines.bot:
                self.buy()
        else:
            # Sell condition
            if self.rsi > 70 and self.macd.macd < self.macd.signal and self.data.close > self.bbands.lines.top:
                self.sell()


def backtest(strategy, data):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy)
    cerebro.adddata(data)
    cerebro.run()


def bullish(symbol):
    # Place your logic here for bullish signal
    # We are using Moving Average Convergence Divergence (MACD), Relative Strength Index (RSI), and Bollinger Bands as indicators for buying signals
    bars = yf.download(symbol, period="1mo")
    close_prices = bars['Close']
    macd, macdsignal, macdhist = MACD(close_prices)
    rsi = RSI(close_prices)
    upper, middle, lower = BBANDS(close_prices)

    # Generate signals based on the indicators
    macd_signal = macd[-1] > macdsignal[-1]  # MACD crosses above signal line
    rsi_signal = rsi[-1] < 30  # RSI is below 30 (Oversold)
    bollinger_signal = close_prices[-1] < lower[-1]  # Price crosses below lower Bollinger Band

    return macd_signal and rsi_signal and bollinger_signal


def bearish(symbol):
    # Place your logic here for bearish signal
    # We are using Moving Average Convergence Divergence (MACD), Relative Strength Index (RSI), and Bollinger Bands as indicators for selling signals
    bars = yf.download(symbol, period="1mo")
    close_prices = bars['Close']
    macd, macdsignal, macdhist = MACD(close_prices)
    rsi = RSI(close_prices)
    upper, middle, lower = BBANDS(close_prices)

    # Generate signals based on the indicators
    macd_signal = macd[-1] < macdsignal[-1]  # MACD crosses below signal line
    rsi_signal = rsi[-1] > 70  # RSI is above 70 (Overbought)
    bollinger_signal = close_prices[-1] > upper[-1]  # Price crosses above upper Bollinger Band

    return macd_signal and rsi_signal and bollinger_signal


def evaluate_stock(symbol):
    df = yf.download(symbol, period="1y")
    df["RSI"] = RSI(df["Close"], timeperiod=14)
    df["MACD"], _, _ = MACD(df["Close"], fastperiod=12, slowperiod=26, signalperiod=9)
    df["Upper Band"], df["Middle Band"], df["Lower Band"] = BBANDS(df["Close"], timeperiod=20)

    data = bt.feeds.PandasData(dataname=df)

    backtest(MyStrategy, data)

    # Calculate the percentage change from the initial value to the final value
    initial_value = df["Close"].iloc[0]
    final_value = df["Close"].iloc[-1]
    percent_change = (final_value - initial_value) / initial_value * 100

    # Print evaluation results with bullish/bearish indication
    print(f"Evaluation results for {symbol}:")
    print(f"RSI: {df['RSI'].iloc[-1]:.2f}")
    print(f"MACD: {df['MACD'].iloc[-1]:.2f}")
    print(f"Bollinger Bands: {df['Upper Band'].iloc[-1]:.2f} - {df['Middle Band'].iloc[-1]:.2f} - {df['Lower Band'].iloc[-1]:.2f}")
    print(f"Percentage change: {percent_change:.2f}%")
    print(f"Bullish: {bullish(symbol)}")
    print(f"Bearish: {bearish(symbol)}")
    print("--------------------")

    # Log evaluation results with bullish/bearish indication
    logging.info(f"Evaluation results for {symbol}:")
    logging.info(f"RSI: {df['RSI'].iloc[-1]:.2f}")
    logging.info(f"MACD: {df['MACD'].iloc[-1]:.2f}")
    logging.info(
        f"Bollinger Bands: {df['Upper Band'].iloc[-1]:.2f} - {df['Middle Band'].iloc[-1]:.2f} - {df['Lower Band'].iloc[-1]:.2f}")
    logging.info(f"Percentage change: {percent_change:.2f}%")
    logging.info(f"Bullish: {bullish(symbol)}")
    logging.info(f"Bearish: {bearish(symbol)}")
    logging.info("--------------------")

def buy_stock(symbol, cash):
    # Get account and check day trade count
    account = api.get_account()
    if account.daytrade_count >= 2:
        print("Day trade limit reached. Not buying.")
        return

    # Get the last closing price of the stock
    bars = yf.download(symbol, period="1d")
    price = bars['Close'].iloc[-1]

    # Calculate the maximum number of shares we can buy
    num_shares = int(cash / price)

    # If we can't buy at least 1 share, then don't submit the order
    if num_shares < 1:
        print(f"Not enough cash to buy a single share of {symbol}")
        return

    # Submit the order
    api.submit_order(
        symbol=symbol,
        qty=num_shares,
        side='buy',
        type='market',
        time_in_force='day'
    )
    print(f"Submitted order to buy {num_shares} shares of {symbol}")


def sell_stock(position):
    # Get account and check day trade count
    account = api.get_account()
    if account.daytrade_count >= 3:
        print("Day trade limit reached. Not selling.")
        return

    if position.qty > 0:
        # Submit an order to sell all shares of this stock
        api.submit_order(
            symbol=position.symbol,
            qty=position.qty,
            side='sell',
            type='market',
            time_in_force='day'
        )
        print(f"Submitted order to sell all shares of {position.symbol}")



def monitor_stocks():
    while True:
        # Print account information
        print_account_info()

        # Print current positions
        print_positions()

        # Evaluate and print monitored stocks
        for symbol in SYMBOLS:
            evaluate_stock(symbol)

        # Sleep for 1 minute before checking again
        time.sleep(60)


if __name__ == "__main__":
    while True:
        try:
            monitor_stocks()
        except Exception as e:
            print(f"Error: {e}")
            logging.error(f"Error: {e}")
            # Sleep for 5 seconds before restarting the program
            time.sleep(5)
            continue