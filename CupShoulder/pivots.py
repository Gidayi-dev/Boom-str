import pandas as pd
import numpy as np

def find_pivots(df, left=3, right=3):
    """
    Fractal-style swing high/low detection.
    A candle at index i is a swing HIGH if its high is the max among
    [i-left, i+right]. Swing LOW likewise for lows.
    Returns df with 'pivot' column: 1 = swing high, -1 = swing low, 0 = none.
    """
    highs = df['high'].values
    lows = df['low'].values
    n = len(df)
    pivot = np.zeros(n, dtype=int)

    for i in range(left, n - right):
        window_high = highs[i-left:i+right+1]
        window_low = lows[i-left:i+right+1]
        if highs[i] == window_high.max() and np.argmax(window_high) == left:
            pivot[i] = 1
        elif lows[i] == window_low.min() and np.argmin(window_low) == left:
            pivot[i] = -1

    df = df.copy()
    df['pivot'] = pivot
    return df

if __name__ == "__main__":
    df = pd.read_csv('boom1000_1h.csv', parse_dates=['time'])
    df = find_pivots(df, left=3, right=3)
    highs = df[df['pivot'] == 1]
    lows = df[df['pivot'] == -1]
    print(f"Found {len(highs)} swing highs, {len(lows)} swing lows out of {len(df)} candles")
    print(highs[['time','high']].head())
    print(lows[['time','low']].head())