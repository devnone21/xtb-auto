from _init import *
from redis.exceptions import ConnectionError
from datetime import datetime
import pandas as pd
LOGGER.setLevel(logging.DEBUG)


def indicator_signal(symbol):
    # get charts
    now = int(datetime.now().timestamp())
    digits = 5
    rate_infos = []
    LOGGER.info(f'recv {symbol} {len(rate_infos)} ticks.')
    # caching
    try:
        cache = Cache()
        for ctm in rate_infos:
            cache.set_key(f'{symbol}_{conf.period}:{ctm["ctm"]}', ctm)
        ctm_prefix = range(((now - 360_000) // 100_000), (now // 100_000)+1)
        rate_infos = []
        for pre in ctm_prefix:
            mkey = cache.client.keys(pattern=f'{symbol}_{conf.period}:{pre}*')
            rate_infos.extend(cache.get_keys(mkey))
    except ConnectionError as e:
        LOGGER.error(e)
    # prepare candles
    if not rate_infos:
        return None, {}
    rate_infos.sort(key=lambda x: x['ctm'])
    candles = pd.DataFrame(rate_infos)
    candles['close'] = (candles['open'] + candles['close']) / 10 ** digits
    candles['high'] = (candles['open'] + candles['high']) / 10 ** digits
    candles['low'] = (candles['open'] + candles['low']) / 10 ** digits
    candles['open'] = candles['open'] / 10 ** digits
    LOGGER.info(f'got {symbol} {len(candles)} ticks.')
    # evaluate
    from signals import Fx
    fx = Fx(algo=conf.algorithm, tech=conf.tech)
    action, mode = fx.evaluate(candles)
    epoch_ms = fx.candles.iloc[-1]['ctm']
    return fx.candles, {"epoch_ms": epoch_ms, "action": action, "mode": mode}


def run():
    report = Notify()
    LOGGER.debug('Enter the Gate.')

    for symbol in conf.symbols:
        # Market open, check signal
        df, signal = indicator_signal(symbol)
        if not signal:
            continue
        price = df.iloc[-1]['close']
        action = signal.get("action")
        mode = signal.get("mode")
        ts = report.setts(datetime.fromtimestamp(int(signal.get("epoch_ms"))/1000))
        report.print_notify(f'\nSignal: {symbol}, {ts}, {action}, {mode.upper()}, {price}')
        LOGGER.debug(df.tail(2).head(1).iloc[:, [0, 1, -4, -3, -2, -1]].to_string(header=False))
        LOGGER.debug(df.tail(1).iloc[:, [0, 1, -4, -3, -2, -1]].to_string(header=False))
        
        # Check signal to open/close transaction
        if action.upper() in ('OPEN',):
            res = "OK"
            report.print_notify(f'>> Open trade: {symbol} at {ts} of {conf.volume} with {mode.upper()}, {res}')
        if action.upper() in ('CLOSE',):
            res = "OK"
            report.print_notify(f'>> Close opened trades: {symbol} at {ts} with {mode.upper()}, {res}')


if __name__ == '__main__':
    run()
