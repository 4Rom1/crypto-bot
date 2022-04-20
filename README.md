## Simple simulation trading bot
Simulation trading bot that selects a currency pair based on a low relative strength index (RSI).   
The bot uses [python-binance api](https://python-binance.readthedocs.io/en/latest/).  
**This is only a simulation, buy or sell order isn't actually performed**, but it gives you the percentage of benefits you'll have if you were to buy or sell in a real time environment.  

It fetches among all available pairs ending with USDT and select the ones that respect the criteria (low RSI and bullish trend).  
It retrieves real time data and averages the signal (bid and ask price) over a period of user defined number of seconds of spaced signal.  
The signal to buy is given when  
- The RSI is lower than a user defined value (default 40).
- When there is a bullish trend (comparing recent average to older one).
- There is a series of successive increasing close values.
- when the averaged volume is bigger than a user defined value.    

The signal to sell is given when   
- The bid price reaches a stop loss defined according to the ATR (average true range) computed over a window of 5 minutes steps
- when it reaches the take profit value defined by the the maximal value (max-min) over a user defined window of 5 minutes steps
- when it goes down after successive bullish values and the calculated profit is bigger than a user defined value.  

## Installation 
- Obtain keys from the [binance test API](https://testnet.binance.vision), and store it in .env file as described in [python-decouple documentation](https://pypi.org/project/python-decouple/#env-file).
- Install the required packages with: 
  > pip3 install -r requirement.txt
- Run with : 
  > python3 simulation_bot.py
- Show argument help:
  > python3 simulation_bot.py --help   
