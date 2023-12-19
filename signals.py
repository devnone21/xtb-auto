from pandas import DataFrame, concat
from pandas_ta.utils import signals as ta_signals
import pandas_ta as ta


def _add_signal(df: DataFrame, ind_name, **kwargs):
    ind = df[ind_name]
    signalsdf = concat(
        [
            df,
            ta_signals(
                indicator=ind,
                xa=kwargs.pop("xa", 80),
                xb=kwargs.pop("xb", 20),
                xserie=kwargs.pop("xserie", None),
                xserie_a=kwargs.pop("xserie_a", None),
                xserie_b=kwargs.pop("xserie_b", None),
                cross_values=kwargs.pop("cross_values", False),
                cross_series=kwargs.pop("cross_series", True),
                offset=None,
            ),
        ],
        axis=1,
    )
    return signalsdf


class Fx:
    def __init__(self, algo: str, tech=None, candles=None):
        self.name = algo.lower()
        self.tech = tech
        self.candles = candles
        self.orig_candles = candles

    def evaluate(self, candles: DataFrame):
        self.candles = self.orig_candles = candles
        # apply technical analysis (TA)
        self.candles.ta.strategy(ta.Strategy(name=self.name, ta=self.tech))
        self.candles.dropna(inplace=True, ignore_index=True)
        func = getattr(Fx, f'_evaluate_{self.name}')
        return func(self)

    def _evaluate_macd(self):
        """As evaluate function, takes DataFrame candles contains 'MACD..._XA_0' column,
        return: (str)what_to_action, (str)mode_buy_or_sell.
        """
        self.name = 'macd'
        cols = self.candles.columns.to_list()
        col_xa = {'name': c for c in cols if c.startswith('MACD') and ('_XA_' in c)}
        col_xb = {'name': c for c in cols if c.startswith('MACD') and ('_XB_' in c)}
        if not col_xa or not col_xb:
            return 'stay', 'na'
        buy_signal = self.candles[col_xa['name']].iloc[-1]
        sell_signal = self.candles[col_xb['name']].iloc[-1]
        if sum([buy_signal, sell_signal]) == 1:
            if buy_signal == 1: return 'open', 'buy'
            if sell_signal == 1: return 'open', 'sell'
        return 'stay', 'wait'

    def _evaluate_rsi(self):
        """As evaluate function, takes DataFrame candles contains 'RSI..._A_' or 'RSI..._B_' column,
        return: (str)what_to_action, (str)mode_buy_or_sell.
        """
        self.name = 'rsi'
        cols = self.candles.columns.to_list()
        col_a = {'name': c for c in cols if c.startswith('RSI') and ('_A_' in c)}
        col_b = {'name': c for c in cols if c.startswith('RSI') and ('_B_' in c)}
        if not col_a or not col_b:
            return 'stay', 'na'
        last_rsi = self.candles[[col_a['name'], col_b['name']]].iloc[-2:].values.tolist()  # [[0, 0], [1, 0]]
        bit_array = sum(last_rsi, start=[])                                                 # [0, 0, 1, 0]
        if sum(bit_array) == 1:
            bit_position = sum([n * (i + 1) for i, n in enumerate(bit_array)])
            if bit_position == 1: return 'open', 'sell'
            if bit_position == 2: return 'open', 'buy'
            if bit_position == 3: return 'close', 'buy'
            if bit_position == 4: return 'close', 'sell'
        return 'stay', 'wait'

    def _evaluate_stoch(self):
        """As evaluate function, takes DataFrame candles contains 'STOCHk...' column,
        return: (str)what_to_action, (str)mode_buy_or_sell.
        """
        self.name = 'stoch'
        # add signal
        cols = self.candles.columns.to_list()
        col_stk = {'name': c for c in cols if c.startswith('STOCHk')}
        if not col_stk:
            return 'stay', 'na'
        self.candles = _add_signal(self.candles, col_stk['name'], xa=80, xb=20)
        # actual evaluate
        cols = self.candles.columns.to_list()
        col_a = {'name': c for c in cols if c.startswith('STOCH') and ('_A_' in c)}
        col_b = {'name': c for c in cols if c.startswith('STOCH') and ('_B_' in c)}
        if not col_a or not col_b:
            return 'stay', 'na'
        last_ind = self.candles[[col_a['name'], col_b['name']]].iloc[-2:].values.tolist()  # [[0, 0], [1, 0]]
        bit_array = sum(last_ind, start=[])                                                 # [0, 0, 1, 0]
        if sum(bit_array) == 1:
            bit_position = sum([n * (i + 1) for i, n in enumerate(bit_array)])
            if bit_position == 1: return 'open', 'sell'
            if bit_position == 2: return 'open', 'buy'
            if bit_position == 3: return 'close', 'buy'
            if bit_position == 4: return 'close', 'sell'
        return 'stay', 'wait'
