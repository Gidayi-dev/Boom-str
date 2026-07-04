
import pandas as pd
import os
from config import OUTCOME_HORIZONS_MIN as HORIZONS_MIN, WIN_THRESHOLD_PCT, LOSS_THRESHOLD_PCT
 
JOURNAL_COLUMNS = (
    ['pattern_id', 'left_rim_time', 'bottom_time', 'right_rim_time', 'handle_time',
     'breakout_time', 'breakout_price', 'retest_time', 'retest_price', 'cup_depth_pct', 'handle_depth_pct']
    + [f'price_{h}min' for h in HORIZONS_MIN]
    + [f'move_{h}min_pct' for h in HORIZONS_MIN]
    + [f'mfe_{h}min_pct' for h in HORIZONS_MIN]
    + [f'mae_{h}min_pct' for h in HORIZONS_MIN]
    + [f'outcome_{h}min' for h in HORIZONS_MIN]
    + ['status', 'notified']
)
 
 
def init_journal(path):
    """Load existing journal, or start a fresh one. If loading an OLDER
    journal.csv that predates a schema change (e.g. before MFE/MAE columns
    existed), missing columns are added as blank so nothing breaks --
    those older rows just won't have MFE/MAE data, which is fine."""
    if os.path.exists(path):
        df = pd.read_csv(path, parse_dates=[
            'left_rim_time', 'bottom_time', 'right_rim_time', 'handle_time',
            'breakout_time', 'retest_time'
        ])
        for col in JOURNAL_COLUMNS:
            if col not in df.columns:
                df[col] = None
        return df
    return pd.DataFrame(columns=JOURNAL_COLUMNS)
 
 
def log_new_patterns(journal_df, patterns_df):
    """Append newly detected patterns that aren't already in the journal
    (deduped by retest_time, since that's the unique trigger moment).
    Returns (updated_journal_df, list_of_newly_added_pattern_ids)."""
    if patterns_df.empty:
        return journal_df, []
 
    known_retests = set(journal_df['retest_time']) if not journal_df.empty else set()
    new_rows = []
    new_ids = []
 
    for _, row in patterns_df.iterrows():
        if pd.isna(row.get('retest_time')) or row['retest_time'] in known_retests:
            continue  # only log patterns that reached a confirmed retest
 
        pattern_id = f"{row['retest_time']}"
        entry = {col: None for col in JOURNAL_COLUMNS}
        entry.update({
            'pattern_id': pattern_id,
            'left_rim_time': row['left_rim_time'],
            'bottom_time': row['bottom_time'],
            'right_rim_time': row['right_rim_time'],
            'handle_time': row['handle_time'],
            'breakout_time': row['breakout_time'],
            'breakout_price': row.get('breakout_price'),
            'retest_time': row['retest_time'],
            'cup_depth_pct': row['cup_depth_pct'],
            'handle_depth_pct': row['handle_depth_pct'],
            'status': 'PENDING',
            'notified': False,
        })
        new_rows.append(entry)
        new_ids.append(pattern_id)
 
    if not new_rows:
        return journal_df, []
 
    updated = pd.concat([journal_df, pd.DataFrame(new_rows)], ignore_index=True)
    return updated, new_ids
 
 
def resolve_pending(journal_df, m1_df):
    """
    For each PENDING pattern, look at the FULL price path (not just a single
    snapshot) between retest_time and retest_time + each horizon, using
    minute-level candles (m1_df: columns time, open, high, low, close).
 
    For each horizon, records:
      - price at exactly that horizon (same as before)
      - MFE: the best price reached in your favor at any point in the window
      - MAE: the worst price reached against you at any point in the window
      - outcome: WIN/LOSS/FLAT based on the price AT the horizon mark (unchanged logic)
 
    Marks a pattern RESOLVED once all horizons have a value.
    """
    m1_df = m1_df.sort_values('time').reset_index(drop=True)
 
    for idx, row in journal_df.iterrows():
        if row['status'] == 'RESOLVED':
            continue
 
        retest_time = row['retest_time']
 
        # retest price = closest candle close at/after retest_time
        retest_candles = m1_df[m1_df['time'] >= retest_time]
        if retest_candles.empty:
            continue
        retest_price = retest_candles.iloc[0]['close']
        journal_df.at[idx, 'retest_price'] = retest_price
 
        all_resolved = True
        for h in HORIZONS_MIN:
            col_price = f'price_{h}min'
            col_move = f'move_{h}min_pct'
            col_mfe = f'mfe_{h}min_pct'
            col_mae = f'mae_{h}min_pct'
            col_outcome = f'outcome_{h}min'
 
            if pd.notna(row.get(col_price)):
                continue  # already resolved this horizon
 
            target_time = retest_time + pd.Timedelta(minutes=h)
 
            # the full path of candles from retest to this horizon (for MFE/MAE)
            window = m1_df[(m1_df['time'] >= retest_time) & (m1_df['time'] <= target_time)]
            future_candles = m1_df[m1_df['time'] >= target_time]
 
            if future_candles.empty or window.empty:
                all_resolved = False  # not enough data yet -- try again later
                continue
 
            future_price = future_candles.iloc[0]['close']
            move_pct = (future_price - retest_price) / retest_price * 100
 
            mfe_pct = (window['high'].max() - retest_price) / retest_price * 100
            mae_pct = (window['low'].min() - retest_price) / retest_price * 100
 
            if move_pct >= WIN_THRESHOLD_PCT:
                outcome = 'WIN'
            elif move_pct <= LOSS_THRESHOLD_PCT:
                outcome = 'LOSS'
            else:
                outcome = 'FLAT'
 
            journal_df.at[idx, col_price] = future_price
            journal_df.at[idx, col_move] = round(move_pct, 4)
            journal_df.at[idx, col_mfe] = round(mfe_pct, 4)
            journal_df.at[idx, col_mae] = round(mae_pct, 4)
            journal_df.at[idx, col_outcome] = outcome
 
        journal_df.at[idx, 'status'] = 'RESOLVED' if all_resolved else 'PENDING'
 
    return journal_df
 
 
def summarize(journal_df):
    """Print win/loss/flat rate AND average MFE/MAE per horizon."""
    print(f"Total patterns logged: {len(journal_df)}")
    resolved = journal_df[journal_df['status'] == 'RESOLVED']
    print(f"Fully resolved: {len(resolved)}  |  Still pending: {len(journal_df) - len(resolved)}\n")
 
    for h in HORIZONS_MIN:
        col = f'outcome_{h}min'
        col_mfe = f'mfe_{h}min_pct'
        col_mae = f'mae_{h}min_pct'
 
        counts = journal_df[col].value_counts()
        total = counts.sum()
        if total == 0:
            print(f"{h} min: no data yet")
            continue
 
        wins = counts.get('WIN', 0)
        losses = counts.get('LOSS', 0)
        flats = counts.get('FLAT', 0)
        win_rate = wins / total * 100
 
        avg_mfe = journal_df[col_mfe].dropna().mean()
        avg_mae = journal_df[col_mae].dropna().mean()
        mfe_str = f"{avg_mfe:+.3f}%" if pd.notna(avg_mfe) else "n/a"
        mae_str = f"{avg_mae:+.3f}%" if pd.notna(avg_mae) else "n/a"
 
        print(f"{h:>2} min after retest -> WIN {wins} ({win_rate:.0f}%) | LOSS {losses} | FLAT {flats}  "
              f"[n={total}]  | Avg MFE {mfe_str} | Avg MAE {mae_str}")
 