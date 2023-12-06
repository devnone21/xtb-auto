def signal_rsi(candles):
    """As evaluate function, takes pandas.DataFrame of candles,
    return: (bool)whether_to_open_position, (str)mode_buy_or_sell.
    """
    cols = candles.columns.to_list()
    col_a = [c for c in cols if c.startswith('RSI') and ('_A_' in c)]
    col_b = [c for c in cols if c.startswith('RSI') and ('_B_' in c)]
    col_a = col_a[0] if col_a else 'close'
    col_b = col_b[0] if col_b else 'close'
    sell_open = candles.iloc[-2][col_a] > candles.iloc[-1][col_a]
    buy_open = candles.iloc[-2][col_b] > candles.iloc[-1][col_b]
    open_tx = sum([sell_open, buy_open]) == 1
    mode = 'buy' if buy_open else 'sell'
    return open_tx, mode


def rsi(candles):
    """As evaluate function, takes pandas.DataFrame of candles,
    return: (bool)whether_to_open_position, (str)mode_buy_or_sell.
    """
    cols = candles.columns.to_list()
    col_a = {'name': c for c in cols if c.startswith('RSI') and ('_A_' in c)}
    col_b = {'name': c for c in cols if c.startswith('RSI') and ('_B_' in c)}
    if not col_a or not col_b:
        return 'Stay', 'NA'
    last_rsi = candles[[col_a['name'], col_b['name']]].iloc[-2:].values.tolist()    # [[0, 0], [1, 0]]
    bit_array = sum(last_rsi, start=[])                                              # [0, 0, 1, 0]
    if sum(bit_array) == 1:
        bit_position = sum([n*(i+1) for i, n in enumerate(bit_array)])
        if bit_position == 1: return 'Open', 'sell'
        if bit_position == 2: return 'Open', 'buy'
        if bit_position == 3: return 'Close', 'buy'
        if bit_position == 4: return 'Close', 'sell'
    return 'Stay', 'Wait'
