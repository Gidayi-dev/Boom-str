import pandas as pd
import os
from config import OUTCOME_HORIZONS_MIN as HORIZONS_MIN, WIN_THRESHOLD_PCT, LOSS_THRESHOLD_PCT
JOURNAL_COLUMNS = (
    ['pattern_id', 'left_rim_time', 'bottom_time', 'right_rim_time', 'handle_time',
     'breakout_time', 'breakout_price', 'retest_time', 'retest_price', 'cup_depth_pct', 'handle_depth_pct']
    + [f'price_{h}min' for h in HORIZONS_MIN]
    + [f'move_{h}min_pct' for h in HORIZONS_MIN]
    + [f'outcome_{h}min' for h in HORIZONS_MIN]
    + ['status', 'notified']
)


def init_journal(path):
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=[
            'left_rim_time', 'bottom_time', 'right_rim_time', 'handle_time',
            'breakout_time', 'retest_time'
        ])
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
    For each PENDING pattern, look up price at retest_time + each horizon
    using minute-level candles (m1_df: columns time, open, high, low, close).
    Classifies each horizon as WIN / LOSS / FLAT based on % move from retest price.
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
            col_outcome = f'outcome_{h}min'

            if pd.notna(row.get(col_price)):
                continue  

            target_time = retest_time + pd.Timedelta(minutes=h)
            future_candles = m1_df[m1_df['time'] >= target_time]

            if future_candles.empty:
                all_resolved = False 
                continue

            future_price = future_candles.iloc[0]['close']
            move_pct = (future_price - retest_price) / retest_price * 100

            if move_pct >= WIN_THRESHOLD_PCT:
                outcome = 'WIN'
            elif move_pct <= LOSS_THRESHOLD_PCT:
                outcome = 'LOSS'
            else:
                outcome = 'FLAT'

            journal_df.at[idx, col_price] = future_price
            journal_df.at[idx, col_move] = round(move_pct, 4)
            journal_df.at[idx, col_outcome] = outcome

        journal_df.at[idx, 'status'] = 'RESOLVED' if all_resolved else 'PENDING'

    return journal_df


def summarize(journal_df):
    """Print win/loss/flat rate per horizon across all resolved+partial entries."""
    print(f"Total patterns logged: {len(journal_df)}")
    resolved = journal_df[journal_df['status'] == 'RESOLVED']
    print(f"Fully resolved: {len(resolved)}  |  Still pending: {len(journal_df) - len(resolved)}\n")

    for h in HORIZONS_MIN:
        col = f'outcome_{h}min'
        counts = journal_df[col].value_counts()
        total = counts.sum()
        if total == 0:
            print(f"{h} min: no data yet")
            continue
        wins = counts.get('WIN', 0)
        losses = counts.get('LOSS', 0)
        flats = counts.get('FLAT', 0)
        win_rate = wins / total * 100
        print(f"{h:>2} min after retest -> WIN {wins} ({win_rate:.0f}%) | LOSS {losses} | FLAT {flats}  [n={total}]")