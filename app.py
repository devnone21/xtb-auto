from _init import *
from XTBApi.api import Client
from redis.exceptions import ConnectionError
from datetime import datetime
import pandas as pd
LOGGER.setLevel(logging.DEBUG)


def indicator_signal(client, symbol):
    # get charts
    now = int(datetime.now().timestamp())
    res = client.get_chart_range_request(symbol, conf.period, now, now, -100)
    digits = res['digits']
    rate_infos = res['rateInfos']
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
    client = Client()
    client.login(conf.race_name, conf.race_pass, mode=conf.race_mode)
    report = Notify()
    LOGGER.debug('Enter the Gate.')

    # Check if market is open
    market_status = client.get_market_status(conf.symbols)
    report.print_notify(f'[{conf.algorithm.upper()}_{conf.period}] Market status: {market_status}')
    for symbol in market_status.keys():
        if not market_status[symbol]:
            continue

        # Market open, check signal
        df, signal = indicator_signal(client, symbol)
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
            res = trigger_open_trade(client, symbol=symbol, mode=mode)
            report.print_notify(f'>> Open trade: {symbol} at {ts} of {conf.volume} with {mode.upper()}, {res}')
        if action.upper() in ('CLOSE',):
            res = trigger_close_trade(client, symbol=symbol, mode=mode)
            report.print_notify(f'>> Close opened trades: {symbol} at {ts} with {mode.upper()}, {res}')

    store_trade_rec(client)
    client.logout()
    # gcp = Cloud()
    # gcp.pub(report.texts)


if __name__ == '__main__':
    run()
