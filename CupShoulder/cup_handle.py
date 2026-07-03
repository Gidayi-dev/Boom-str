import pandas as pd
import numpy as np
from pivots import find_pivots

def scan_cup_and_handle(
    df,
    min_cup_bars=15,     
    max_cup_bars=150,    
    rim_tolerance=0.02,    
    min_cup_depth=0.015,   
    max_cup_depth=0.15, 
    min_handle_bars=8,     
    max_handle_bars=40,    
    max_handle_depth_ratio=0.5,  
    breakout_lookahead=40, 
    retest_tolerance=0.01, 
    retest_lookahead=20,   
):
    piv = find_pivots(df, left=3, right=3).reset_index(drop=True)
    highs_idx = piv.index[piv['pivot'] == 1].tolist()
    lows_idx = piv.index[piv['pivot'] == -1].tolist()

    patterns = []

    for bottom_i in lows_idx:
        bottom_price = piv.loc[bottom_i, 'low']

        left_candidates = [h for h in highs_idx if h < bottom_i]
        if not left_candidates:
            continue
        left_i = left_candidates[-1]
        left_price = piv.loc[left_i, 'high']

        right_candidates = [h for h in highs_idx if h > bottom_i]
        right_i = None
        for h in right_candidates:
            cup_len = h - left_i
            if cup_len > max_cup_bars:
                break
            if cup_len < min_cup_bars:
                continue
            rim_diff = abs(piv.loc[h, 'high'] - left_price) / left_price
            if rim_diff <= rim_tolerance:
                right_i = h
                right_price = piv.loc[h, 'high']
                break
        if right_i is None:
            continue

        rim_avg = (left_price + right_price) / 2
        depth = (rim_avg - bottom_price) / rim_avg
        if not (min_cup_depth <= depth <= max_cup_depth):
            continue

        handle_lows = [l for l in lows_idx if right_i < l <= right_i + max_handle_bars]
        if not handle_lows:
            continue
        handle_i = handle_lows[0]
        handle_price = piv.loc[handle_i, 'low']
        handle_depth = (right_price - handle_price) / right_price

        if handle_price <= bottom_price:
            continue  
        if handle_depth > depth * max_handle_depth_ratio:
            continue 

        search_start = handle_i + 1
        search_end = min(search_start + breakout_lookahead, len(df) - 1)
        breakout_i = None
        for j in range(search_start, search_end):
            if df.loc[j, 'close'] > rim_avg:
                breakout_i = j
                break
        if breakout_i is None:
            continue

        handle_span_bars = breakout_i - right_i
        if handle_span_bars < min_handle_bars:
            continue

        handle_window = df.loc[right_i:breakout_i]
        pullback_candles = (handle_window['low'] < right_price).sum()
        if pullback_candles < 2:
            continue
        
        retest_start = breakout_i + 1
        retest_end = min(retest_start + retest_lookahead, len(df) - 1)
        retest_i = None
        for k in range(retest_start, retest_end):
            near_rim = abs(df.loc[k, 'low'] - rim_avg) / rim_avg <= retest_tolerance
            held = df.loc[k, 'close'] >= rim_avg * (1 - retest_tolerance)
            if near_rim and held:
                retest_i = k
                break

        patterns.append({
            'left_rim_time': df.loc[left_i, 'time'], 'left_rim_price': left_price,
            'bottom_time': df.loc[bottom_i, 'time'], 'bottom_price': bottom_price,
            'right_rim_time': df.loc[right_i, 'time'], 'right_rim_price': right_price,
            'handle_time': df.loc[handle_i, 'time'], 'handle_price': handle_price,
            'breakout_time': df.loc[breakout_i, 'time'], 'breakout_price': df.loc[breakout_i, 'close'],
            'retest_time': df.loc[retest_i, 'time'] if retest_i else None,
            'cup_depth_pct': round(depth * 100, 2),
            'handle_depth_pct': round(handle_depth * 100, 2),
            'status': 'RETEST_CONFIRMED' if retest_i else 'BREAKOUT_ONLY_NO_RETEST_YET',
        })

    return pd.DataFrame(patterns)


if __name__ == "__main__":
    df = pd.read_csv('boom1000_1h.csv', parse_dates=['time'])
    results = scan_cup_and_handle(df)
    print(f"Found {len(results)} cup-and-handle patterns\n")
    if len(results):
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', 200)
        print(results.to_string())