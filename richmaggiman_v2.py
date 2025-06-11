import ccxt
import pandas as pd
import mplfinance as mpf
import datetime
import os
import csv
import pytz
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

# User Settings
symbol = 'BTC/USDT'
timeframe = '1h'
exchange = ccxt.binance()
limit = 200
journal_file = 'richmaggiman_journal.csv'

# Make sure journal file exists
if not os.path.isfile(journal_file):
    with open(journal_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Time', 'Symbol', 'Type', 'Entry', 'SL', 'TP'])

# Fetch data
data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# Indicators
ema_20 = EMAIndicator(df['close'], window=20).ema_indicator()
ema_50 = EMAIndicator(df['close'], window=50).ema_indicator()
rsi = RSIIndicator(df['close'], window=14).rsi()

# Append indicators
df['EMA20'] = ema_20
df['EMA50'] = ema_50
df['RSI'] = rsi

# Signal generation
def generate_signals(df):
    signals = []
    for i in range(1, len(df)):
        row, prev = df.iloc[i], df.iloc[i - 1]
        long_signal = (
            prev['EMA20'] < prev['EMA50'] and row['EMA20'] > row['EMA50']
            and row['RSI'] > 50
        )
        short_signal = (
            prev['EMA20'] > prev['EMA50'] and row['EMA20'] < row['EMA50']
            and row['RSI'] < 50
        )

        if long_signal:
            entry = row['close']
            sl = entry * 0.98
            tp = entry * 1.05
            signals.append((df.index[i], 'LONG', entry, sl, tp))
        elif short_signal:
            entry = row['close']
            sl = entry * 1.02
            tp = entry * 0.95
            signals.append((df.index[i], 'SHORT', entry, sl, tp))
    return signals

signals = generate_signals(df)

# Plotting
apds = [
    mpf.make_addplot(df['EMA20'], color='lime'),
    mpf.make_addplot(df['EMA50'], color='orange')
]

arrow_up = [np.nan] * len(df)
arrow_down = [np.nan] * len(df)

for i, (signal_time, signal_type, entry, sl, tp) in enumerate(signals):
    if signal_time in df.index:
        idx = df.index.get_loc(signal_time)
        if signal_type == 'LONG':
            arrow_up[idx] = df['low'].iloc[idx] * 0.995
        elif signal_type == 'SHORT':
            arrow_down[idx] = df['high'].iloc[idx] * 1.005

apds.append(mpf.make_addplot(arrow_up, scatter=True, markersize=100, marker='^', color='green'))
apds.append(mpf.make_addplot(arrow_down, scatter=True, markersize=100, marker='v', color='red'))

# Save signals to journal
with open(journal_file, 'a', newline='') as f:
    writer = csv.writer(f)
    for signal_time, signal_type, entry, sl, tp in signals:
        writer.writerow([signal_time, symbol, signal_type, round(entry, 2), round(sl, 2), round(tp, 2)])

# Show chart
mpf.plot(df, type='candle', style='charles', addplot=apds,
         title=f'{symbol} - RICHMAGGIMAN Signals', ylabel='Price',
         volume=True)

print("\n✔ App run complete. Chart rendered. Trade journal updated.")
