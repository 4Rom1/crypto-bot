import matplotlib.dates as mpldates
import matplotlib.pyplot as plt
from mplfinance.original_flavor import candlestick_ohlc
import pandas as pd


def sign(x):
    return -1 if x < 0 else 1


def MaxDiffWindow(arr, k):

    maxdiff = 0

    for i in range(len(arr) - k + 1):
        local_max = arr[i]
        local_min = arr[i]
        for j in range(1, k):
            if arr[i + j] > local_max:
                local_max = arr[i + j]
            if arr[i + j] < local_min:
                local_min = arr[i + j]

        maxdiff = max(maxdiff, local_max-local_min)

    return maxdiff


def show_chart(data, savedcoin):
    ohlc = data.loc[:, ['O time', 'Open', 'High', 'Low', 'Close']]
    ohlc['O time'] = pd.to_datetime(ohlc['O time'])
    ohlc['O time'] = ohlc['O time'].apply(mpldates.date2num)
    ohlc = ohlc.astype(float)

    fig, ax = plt.subplots()

    candlestick_ohlc(ax, ohlc.values, width=0.0003, colorup='green', colordown='red', alpha=0.8)

    ax.set_xlabel('Date')
    ax.set_ylabel('Price')
    fig.suptitle(f'Candlestick Chart for {savedcoin}')

    date_format = mpldates.DateFormatter('%H:%M:%S')
    ax.xaxis.set_major_formatter(date_format)
    fig.autofmt_xdate()

    fig.tight_layout()

    plt.show()


def convert_to_float(_dict):
    for k, v in _dict.items():
        if k != "symbol":
            _dict[k] = float(v)
    return _dict
