from dotenv import load_dotenv, find_dotenv
from redis.client import Redis
from redis.exceptions import ConnectionError
from datetime import datetime
import json
import os
import pandas as pd
import pandas_ta as ta

# Initial parameters: [.env, settings.json]
load_dotenv(find_dotenv())
r_name = os.getenv("RACE_NAME")
r_pass = os.getenv("RACE_PASS")
r_mode = os.getenv("RACE_MODE")
settings = json.load(open('settings.json'))
algorithm = str(settings.get('algorithm', 'rsi'))
tech = settings.get(f'TA_{algorithm.upper()}')
symbols = settings.get('symbols')
volume = settings.get('volume')
rate_tp = settings.get('rate_tp')
rate_sl = settings.get('rate_sl')


class Cache:
    def __init__(self):
        self.ttl_s = 604_800
        self.client = Redis(
            host=os.getenv("REDIS_HOST"),
            port=os.getenv("REDIS_PORT"),
            decode_responses=True
        )

    def set_key(self, key, value):
        self.client.set(key, json.dumps(value), ex=self.ttl_s)

    def get_key(self, key):
        return json.loads(self.client.get(key))

    def get_keys(self, keys):
        return [json.loads(s) for s in self.client.mget(keys)]


class Notify:
    def __init__(self):
        self.ts = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        self.texts = ''

    def setts(self, ts):
        self.ts = ts
        return ts

    def add(self, message):
        self.texts += f'{message}\n'
        return message

    def print_notify(self, message):
        self.add(message)
        print(message)


def indicator_signal(symbol):
    # get charts
    period = settings.get('timeframe', 15)
    now = int(datetime.now().timestamp())
    digits = 5
    rate_infos = []
    print(f'Info: recv {symbol} {len(rate_infos)} ticks.')
    # caching
    try:
        cache = Cache()
        for ctm in rate_infos:
            cache.set_key(f'{symbol}_{period}:{ctm["ctm"]}', ctm)
        ctm_prefix = range(((now - 360_000) // 100_000), (now // 100_000)+1)
        rate_infos = []
        for pre in ctm_prefix:
            mkey = cache.client.keys(pattern=f'{symbol}_{period}:{pre}*')
            rate_infos.extend(cache.get_keys(mkey))
    except ConnectionError as e:
        print(e)
    # tech calculation
    rate_infos.sort(key=lambda x: x['ctm'])
    candles = pd.DataFrame(rate_infos)
    candles['close'] = candles['open'] / 10 ** digits
    print(f'Info: got {symbol} {len(candles)} ticks.')
    ta_strategy = ta.Strategy(
        name="Multi-Momo",
        ta=tech,
    )
    candles.ta.strategy(ta_strategy)
    # clean
    candles.dropna(inplace=True, ignore_index=True)
    print(f'Info: cleaned {symbol} {len(candles)} ticks.')
    # evaluate
    from signals import Fx
    fx = Fx(algo=algorithm, tech=tech)
    action, mode = fx.evaluate(candles)
    epoch_ms = candles.iloc[-1]['ctm']
    return candles, {"epoch_ms": epoch_ms, "action": action, "mode": mode}


def trigger_open_trade():
    return "OK"


def trigger_close_trade():
    # TODO: res = trigger_close_trade()
    return "OK"


def run():
    report = Notify()
    print('Enter the Gate.')

    for symbol in symbols:
        # Market open, check signal
        df, signal = indicator_signal(symbol)
        price = df.iloc[-1]['close']
        action = signal.get("action")
        mode = signal.get("mode")
        ts = report.setts(datetime.fromtimestamp(int(signal.get("epoch_ms"))/1000))
        report.print_notify(f'\nSignal: {symbol}, {ts}, {action}, {mode.upper()}, {price}')
        print(df.iloc[-5:, [0, 1, -3, -2, -1]].to_string(header=False))
        
        # Check signal to open/close transaction
        if action.upper() in ('OPEN',):
            res = trigger_open_trade()
            report.print_notify(f'>> Open trade: {symbol} at {ts} of {volume} with {mode.upper()}, {res}')
        if action.upper() in ('CLOSE',):
            res = trigger_close_trade()
            report.print_notify(f'>> Close opened trades: {symbol} at {ts} with {mode.upper()}, {res}')


if __name__ == '__main__':
    run()
