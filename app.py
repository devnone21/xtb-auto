from XTBApi.api import Client
from XTBApi.exceptions import TransactionRejected
from dotenv import load_dotenv, find_dotenv
from redis.client import Redis
from redis.exceptions import ConnectionError
from datetime import datetime
import json
import os
import pandas as pd
import logging
LOGGER = logging.getLogger('xtb')
LOGGER.setLevel(logging.DEBUG)

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
        LOGGER.info(message.strip())


def indicator_signal(client, symbol):
    # get charts
    period = settings.get('timeframe', 15)
    now = int(datetime.now().timestamp())
    res = client.get_chart_range_request(symbol, period, now, now, -100)
    digits = res['digits']
    rate_infos = res['rateInfos']
    LOGGER.info(f'recv {symbol} {len(rate_infos)} ticks.')
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
        LOGGER.error(e)
    # prepare candles
    rate_infos.sort(key=lambda x: x['ctm'])
    candles = pd.DataFrame(rate_infos)
    candles['close'] = (candles['open'] + candles['close']) / 10 ** digits
    candles['high'] = (candles['open'] + candles['high']) / 10 ** digits
    candles['low'] = (candles['open'] + candles['low']) / 10 ** digits
    candles['open'] = candles['open'] / 10 ** digits
    LOGGER.info(f'got {symbol} {len(candles)} ticks.')
    # evaluate
    from signals import Fx
    fx = Fx(algo=algorithm, tech=tech)
    action, mode = fx.evaluate(candles)
    epoch_ms = fx.candles.iloc[-1]['ctm']
    return fx.candles, {"epoch_ms": epoch_ms, "action": action, "mode": mode}


def trigger_open_trade(client, symbol, mode='buy'):
    try:
        return client.open_trade(mode, symbol, volume, rate_tp=rate_tp, rate_sl=rate_sl)
    except TransactionRejected as e:
        return e


def trigger_close_trade(client, symbol, mode):
    client.update_trades()
    orders = {k: trans.order_id
              for k, trans in client.trade_rec.items() if trans.symbol == symbol and trans.mode == mode}
    LOGGER.debug(f'Order to be closed: {orders}')
    res = {}
    for k, order_id in orders.items():
        try:
            res[k] = client.close_trade_only(order_id)
        except TransactionRejected as e:
            res[k] = f'Exception: {e}'
    return res


def run():
    client = Client()
    client.login(r_name, r_pass, mode=r_mode)
    report = Notify()
    LOGGER.debug('Enter the Gate.')

    # Check if market is open
    market_status = client.get_market_status(symbols)
    report.print_notify(f'[{algorithm.upper()}] Market status: {market_status}')
    for symbol in market_status.keys():
        if not market_status[symbol]:
            continue

        # Market open, check signal
        df, signal = indicator_signal(client, symbol)
        price = df.iloc[-1]['close']
        action = signal.get("action")
        mode = signal.get("mode")
        ts = report.setts(datetime.fromtimestamp(int(signal.get("epoch_ms"))/1000))
        report.print_notify(f'\nSignal: {symbol}, {ts}, {action}, {mode.upper()}, {price}')
        LOGGER.debug(df.iloc[-5:, [0, 1, -4, -3, -2, -1]].to_string(header=False))
        
        # Check signal to open/close transaction
        if action.upper() in ('OPEN',):
            res = trigger_open_trade(client, symbol=symbol, mode=mode)
            report.print_notify(f'>> Open trade: {symbol} at {ts} of {volume} with {mode.upper()}, {res}')
        if action.upper() in ('CLOSE',):
            res = trigger_close_trade(client, symbol=symbol, mode=mode)
            report.print_notify(f'>> Close opened trades: {symbol} at {ts} with {mode.upper()}, {res}')

    client.logout()
    import cloud as gcp
    gcp.pub(report.texts)


if __name__ == '__main__':
    run()
