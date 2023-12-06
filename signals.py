from pandas import DataFrame


class Fx:
    def __init__(self, algo: str):
        self.name = algo.lower()

    def evaluate(self, candles: DataFrame):
        func = getattr(Fx, f'_evaluate_{self.name}')
        return func(self, candles)

    def _evaluate_rsi(self, candles: DataFrame):
        """As evaluate function, takes pandas.DataFrame of candles,
        return: (bool)whether_to_open_position, (str)mode_buy_or_sell.
        """
        self.name = 'rsi'
        cols = candles.columns.to_list()
        col_a = {'name': c for c in cols if c.startswith('RSI') and ('_A_' in c)}
        col_b = {'name': c for c in cols if c.startswith('RSI') and ('_B_' in c)}
        if not col_a or not col_b:
            return 'Stay', 'NA'
        last_rsi = candles[[col_a['name'], col_b['name']]].iloc[-2:].values.tolist()    # [[0, 0], [1, 0]]
        bit_array = sum(last_rsi, start=[])                                             # [0, 0, 1, 0]
        if sum(bit_array) == 1:
            bit_position = sum([n*(i+1) for i, n in enumerate(bit_array)])
            if bit_position == 1: return 'Open', 'sell'
            if bit_position == 2: return 'Open', 'buy'
            if bit_position == 3: return 'Close', 'buy'
            if bit_position == 4: return 'Close', 'sell'
        return 'Stay', 'Wait'

    def _evaluate_macd(self, candles: DataFrame):
        """As evaluate function, takes pandas.DataFrame contains 'MACD..._XA_0' column,
        return: (str)what_to_action, (str)mode_buy_or_sell.
        """
        self.name = 'macd'
        cols = candles.columns.to_list()
        col_xa = {'name': c for c in cols if c.startswith('MACD') and ('_XA_' in c)}
        col_xb = {'name': c for c in cols if c.startswith('MACD') and ('_XB_' in c)}
        if not col_xa or not col_xb:
            return 'Stay', 'NA'
        buy_signal  = candles.iloc[-1][col_xa.get('name')]
        sell_signal = candles.iloc[-1][col_xb.get('name')]
        if sum([buy_signal, sell_signal]) == 1:
            if  buy_signal == 1: return 'Open', 'buy'
            if sell_signal == 1: return 'Open', 'sell'
        return 'Stay', 'Wait'
