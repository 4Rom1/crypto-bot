from decouple import config
from binance.client import Client
import pandas as pd
import pandas_ta as ta
import numpy as np
from time import sleep
import os
from concurrent.futures import ThreadPoolExecutor
import argparse
from utilities import show_chart, MaxDiffWindow, convert_to_float
import pickle


parser = argparse.ArgumentParser(description='Simple bot trading simulation.', formatter_class=argparse.ArgumentDefaultsHelpFormatter)


parser.add_argument('--period', type=int,
                    help=' period for averaging signal', default=20)

parser.add_argument('--sleep-time', type=int, default=5,
                    help='Sleep time between signals in seconds')

parser.add_argument('--history-length', type=int, default=6,
                    help='Numbers of hours to look back into')

parser.add_argument('--profit-ratio', type=float, default=1.5,
                    help='Expected rartio between max profit and target profit')

parser.add_argument('--min-profit', type=float, default=0.3,
                    help='Minimum profit before exiting a trade when price go down')

parser.add_argument('--min-volume', type=float, default=1000,
                    help='Minimum last averaged volume')

parser.add_argument('--min-spread', type=float, default=0.4,
                    help='Minimum allowed spread in percent')

parser.add_argument('--num-atr', type=float, default=3.0,
                    help='Multiplicative factor for the atr to compute the stop loss')

parser.add_argument('--max-min-window', type=float, default=1.0,
                    help='Minimum (max - min) values in percents on a window of 5 minute steps given by --significant-steps argument')

parser.add_argument('--significant-steps', type=int, default=14,
                    help='Numbers of last 5 minutes steps to compare with previous history, and window size')

parser.add_argument('--max-rsi', type=float, default=40,
                    help='Maximum rsi to consider possible trend reversing in an uptrend')

parser.add_argument('--down-move', type=int, default=200,
                    help='Maximum authorised down movement of price before selling (it has to be lower than the bought price)')

parser.add_argument('--successive-bullish', type=int, default=1,
                    help='Number of expected succesive bullish before being selected')

parser.add_argument('--num-try', type=int, default=2,
                    help='Number of successive accepted HTTP requests failures')

parser.add_argument('--show-candle', type=bool, default=False,
                    help='Show candlestick of selected asset')


args = parser.parse_args()

print(f'{args}')

Benefits = 0
profit_ratio = args.profit_ratio
max_min_window = float(args.max_min_window)/100.0
sleep_time = args.sleep_time
period = args.period
min_profit = args.min_profit/100.0
min_volume = args.min_volume
down_move = args.down_move
show_candle = args.show_candle
min_spread = args.min_spread/100.0
history_length = args.history_length
max_rsi = args.max_rsi
significant_steps = args.significant_steps
successive_bullish = args.successive_bullish
num_atr = args.num_atr
window = significant_steps
rsi_lenght = significant_steps
num_try = args.num_try


def fetch_klines(asset, interval, previous_time_step):

    klines = client.get_historical_klines(asset, interval, previous_time_step)

    klines = [x[0:8] for x in klines]
    klines = pd.DataFrame(klines, columns=["O time", "Open", "High", "Low", "Close", "Vol Base", "C time", "Vol quote"])
    klines["O time"] = pd.to_datetime(klines["O time"], unit="ms")
    klines["C time"] = pd.to_datetime(klines["C time"], unit="ms")
    klines["Close"] = klines["Close"].astype("float")
    klines["Open"] = klines["Open"].astype("float")
    klines["Low"] = klines["Low"].astype("float")
    klines["High"] = klines["High"].astype("float")
    klines["Vol Base"] = klines["Vol Base"].astype("float")
    klines["Vol quote"] = klines["Vol quote"].astype("float")
    return klines


def get_rsi(klines, length=rsi_lenght):
    klines['rsi'] = ta.rsi(close=klines['Open'], length=length)
    return klines['rsi'].iloc[-1]


def calculate_metric(data):
    if len(data['Close']) > 2 and len(data['Open']) > 2:
        close = np.array(data['Close'])
        avg_end = np.average(close[-significant_steps:len(close)])
        avg = np.average(close)

        max_diff_window = MaxDiffWindow(close, len(close), window)

        high_low = data['High'] - data['Low']
        high_close = np.abs(data['High'] - data['Close'].shift())
        low_close = np.abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)

        atr = np.average(true_range[-significant_steps:len(true_range)])

        bullish = True
        for i in range(1, successive_bullish):
            bullish = bullish and (data['Close'].iloc[-i-1] < data['Close'].iloc[-i])

        bullish = bullish and avg_end > avg

        RSI = get_rsi(data)

        current = data['Close'].iloc[-1]

        vol = data['Vol quote'].mean()

        if vol > min_volume and bullish and RSI < max_rsi:
            return current, max_diff_window, atr, RSI
        else:
            return 0, 0, 0, 0
    else:
        return 0, 0, 0, 0


def select_max(coin):
    data = fetch_klines(coin['symbol'], Client.KLINE_INTERVAL_5MINUTE, f"{history_length} hours ago UTC")
    current, max_diff_window, atr, rsi = calculate_metric(data)
    sleep(0.1)
    return current, max_diff_window, atr, rsi, coin


if __name__ == "__main__":

    client = Client(config("TEST_API_KEY"), config("TEST_SECRET_KEY"))

    assert(significant_steps < history_length * 12)

    prices = client.get_all_tickers()

    USDTCOIN = [coin for coin in prices if coin['symbol'].endswith('USDT')]

    print(f"Number of coins verifying criteria {len(USDTCOIN)}")

    if os.path.isfile('save_buy.p'):
        BuyDict = pickle.load(open("save_buy.p", "rb"))
    else:
        BuyDict = {}

    while True:
        print("Fetch coins according to criteria")
        if not ("bid_price" in BuyDict):
            cnt = 0
            BuyDict["savedcoin"] = None
            BuyDict["maxratio"] = 0
            BuyDict["rsi"] = 200
            BuyDict["atr_ratio"] = 100
            BuyDict["saved_target"] = 0
            BuyDict["saved_atr"] = 0

            while(BuyDict["savedcoin"] is None):
                with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
                    for current, max_diff_window, atr, rsi, coin in executor.map(select_max, USDTCOIN):
                        if current > 0:
                            ratio_atr = atr/current
                            ratio_diff_window = max_diff_window/current

                            if(BuyDict["rsi"] > rsi and ratio_diff_window > max_min_window):
                                BuyDict["maxratio"] = ratio_diff_window
                                BuyDict["rsi"] = rsi
                                BuyDict["saved_target"] = current + max_diff_window
                                BuyDict["saved_current"] = current
                                BuyDict["savedcoin"] = coin['symbol']
                                BuyDict["saved_atr"] = ratio_atr
                        cnt += 1
                # Sleep if not found to avoid limit requests
                if BuyDict["savedcoin"] is None:
                    print("Fetch again as criteria not met")
                    sleep(20)

        else:
            BuyDict = pickle.load(open("save_buy.p", "rb"))

        savedcoin = BuyDict["savedcoin"]
        maxratio = BuyDict["maxratio"]
        saved_target = BuyDict["saved_target"]
        saved_current = BuyDict["saved_current"]
        saved_atr = BuyDict["saved_atr"]
        saved_rsi = BuyDict["rsi"]

        print(f'Candidate {savedcoin}, maximum window ratio (max-min)/current {maxratio*100}%, target high {saved_target}, current {saved_current}, ATR {saved_atr*100}%, rsi {saved_rsi}')

        data = fetch_klines(savedcoin, Client.KLINE_INTERVAL_5MINUTE, "2 hours ago UTC")
        print(data)
        if show_candle:

            show_chart(data, savedcoin)

        if not ("bid_price" in BuyDict):
            for _ in range(num_try):
                try:
                    coin_price = convert_to_float(client.get_orderbook_ticker(symbol=savedcoin))
                except Exception as e:
                    print(e)
                    sleep(sleep_time)
                    continue
                break

            spread = abs(coin_price['askPrice']-coin_price['bidPrice'])/coin_price['bidPrice']
            print(f"{savedcoin} ask price {coin_price['askPrice']}, spread {spread}")

            if(spread > min_spread):
                print(f"current spread = {spread} is too high")
                break

            buy_price = coin_price['askPrice']
            bid_price = coin_price['bidPrice']

            stop_loss = (1.0-num_atr*saved_atr)*bid_price
            take_profit = (1.0+maxratio/profit_ratio)*buy_price

            BuyDict["take_profit"] = take_profit
            BuyDict["stop_loss"] = stop_loss
            BuyDict["bid_price"] = bid_price
            BuyDict["buy_price"] = buy_price

            pickle.dump(BuyDict, open("save_buy.p", "wb"))
        else:

            take_profit = BuyDict["take_profit"]
            stop_loss = BuyDict["stop_loss"]
            bid_price = BuyDict["bid_price"]
            buy_price = BuyDict["buy_price"]

        print(f"take_profit {take_profit}={(1.0+maxratio/profit_ratio)*100.0} % of price, stop loss {stop_loss}={(1-saved_atr)*100.0} % of price")
        print(f"buy price {buy_price}")
        print(f"Corresponding bid price {bid_price}")

        sleep(sleep_time)

        cnt = 0
        avg_price = bid_price
        last_avg = avg_price
        prev_avg = last_avg

        cnt_down = 0

        while(True):

            for _ in range(num_try):
                try:
                    coin_price = convert_to_float(client.get_orderbook_ticker(symbol=savedcoin))
                except Exception as e:
                    print(e)
                    sleep(sleep_time)
                    continue
                break

            if cnt % period == 0:
                print(f"{coin_price}")
                avg_price = avg_price/period if cnt > 0 else avg_price
                if(prev_avg > last_avg and last_avg < bid_price and cnt_down <= down_move):
                    print(f"last price averaged {last_avg} moved down and price is lower than initial bid price for the {cnt_down+1} time")
                    cnt_down += 1
                print(f"Average price {avg_price}")
                prev_avg = last_avg
                last_avg = avg_price
                avg_price = 0

            if(prev_avg > last_avg and last_avg > bid_price and (last_avg-buy_price)/buy_price > min_profit):
                print(f"last price averaged {last_avg} moved down and profit is bigger than min profit")
                break

            if(coin_price['bidPrice'] > take_profit):
                print(f"Bid price {coin_price['bidPrice']} bigger than take profit {take_profit}")
                break

            if(last_avg < stop_loss):
                print(f"last price averaged {last_avg} lower than stop_loss {stop_loss}")
                break

            if(prev_avg > last_avg and last_avg < bid_price and cnt_down > down_move):
                print(f"last price averaged {last_avg} moved down  more than {down_move} times and price is lower than buy price")
                break

            sleep(sleep_time)

            cnt += 1
            avg_price += coin_price['bidPrice']

        sell_price = coin_price['bidPrice']

        pickle.dump({}, open("save_buy.p", "wb"))

        BuyDict = {}

        print(f"sell_price {sell_price}, difference sell-buy {sell_price-buy_price}, percent {100*(sell_price-buy_price)/sell_price}%")

        # Trading fees are substracted from the benefits
        Benefits += (sell_price-buy_price)/sell_price-0.0015
        print(f"Benefits so far {Benefits*100}%")