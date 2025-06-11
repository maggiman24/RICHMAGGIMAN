import streamlit as st
import ccxt
import pandas as pd
import time
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import datetime

# --- SETTINGS ---
symbol = 'BTC/USDT'
timeframe = '1d'
limit = 100
max_retries = 3
retry_delay = 3

st.set_page_config(layout="wide")
st.title("RICHMAGGIMAN: Crypto Strategy Dashboard")

# --- FETCH DATA WITH RETRY LOGIC ---
def fetch_data(exchange, symbol, timeframe, limit):
    for attempt in range(max_retries):
        try:
            exchange.load_markets()
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            return ohlcv
        except ccxt.NetworkError as e:
            st.warning(f"Network error, retrying... ({attempt+1}/{max_retries})")
            time.sleep(retry_delay)
        except Exception as e:
            st.error(f"Data fetch failed: {str(e)}")
            raise

# --- MAIN ---
try:
    exchange = ccxt.binance()
    ohlcv = fetch_data(exchange, symbol, timeframe, limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    # --- INDICATORS ---
    rsi = RSIIndicator(df['close']).rsi()
    macd = MACD(df['close'])
    bb = BollingerBands(df['close'])

    df['RSI'] = rsi
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['BB_upper'] = bb.bollinger_hband()
    df['BB_lower'] = bb.bollinger_lband()

    # --- SIGNAL LOGIC ---
    df['Signal'] = None
    df.loc[(df['MACD'] > df['MACD_signal']) & (df['RSI'] < 30), 'Signal'] = 'LONG'
    df.loc[(df['MACD'] < df['MACD_signal']) & (df['RSI'] > 70), 'Signal'] = 'SHORT'

    # --- PLOT ---
    apds = [
        mpf.make_addplot(df['RSI'], panel=1, color='green'),
        mpf.make_addplot(df['MACD'], panel=2, color='blue'),
        mpf.make_addplot(df['MACD_signal'], panel=2, color='orange'),
        mpf.make_addplot(df['BB_upper'], color='grey'),
        mpf.make_addplot(df['BB_lower'], color='grey')
    ]

    fig, _ = mpf.plot(
        df,
        type='candle',
        style='yahoo',
        addplot=apds,
        volume=True,
        returnfig=True,
        title=symbol
    )

    st.pyplot(fig)

    # --- SIGNALS TABLE ---
    st.subheader("Trade Signals")
    st.dataframe(df[['close', 'RSI', 'MACD', 'MACD_signal', 'Signal']].dropna())

except Exception as e:
    st.error(f"App failed: {str(e)}")
