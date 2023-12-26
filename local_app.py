from _init import *
from redis.exceptions import ConnectionError
from datetime import datetime
from pandas import DataFrame
LOGGER.setLevel(logging.DEBUG)


class Result:
    def __init__(self, symbol):
        self.symbol = symbol
        self.market_status = False
        self.df = DataFrame()
        self.digits = 5
        self.epoch_ms = 0
        self.price = 0.0
        self.action = ''
        self.mode = ''

    def get_signal(self, client=None):
        # get charts
        now = int(datetime.now().timestamp())
        res = client.get_chart_range_request(self.symbol, conf.period, now, now, -100) if client else {}
        digits = res.get('digits', 5)
        rate_infos = res.get('rateInfos', [])
        LOGGER.debug(f'recv {self.symbol} {len(rate_infos)} ticks.')
        # caching
        try:
            cache = Cache()
            for ctm in rate_infos:
                cache.set_key(f'{conf.race_mode}_{self.symbol}_{conf.period}:{ctm["ctm"]}', ctm)
            ctm_prefix = range(((now - conf.period*60*400) // 100_000), (now // 100_000)+1)
            rate_infos = []
            for pre in ctm_prefix:
                mkey = cache.client.keys(pattern=f'{conf.race_mode}_{self.symbol}_{conf.period}:{pre}*')
                rate_infos.extend(cache.get_keys(mkey))
        except ConnectionError as e:
            LOGGER.error(e)
        # prepare candles
        if not rate_infos:
            return
        rate_infos = [c for c in rate_infos if now - int(c['ctm'])/1000 > conf.period*60]
        rate_infos.sort(key=lambda x: x['ctm'])
        candles = DataFrame(rate_infos)
        candles['close'] = (candles['open'] + candles['close']) / 10 ** digits
        candles['high'] = (candles['open'] + candles['high']) / 10 ** digits
        candles['low'] = (candles['open'] + candles['low']) / 10 ** digits
        candles['open'] = candles['open'] / 10 ** digits
        LOGGER.debug(f'got {self.symbol} {len(candles)} ticks.')
        # evaluate
        from signals import Fx
        fx = Fx(algo=conf.algorithm, tech=conf.tech)
        self.action, self.mode = fx.evaluate(candles)
        self.digits = digits
        self.df = fx.candles
        self.price = self.df.iloc[-1]['close']
        self.epoch_ms = self.df.iloc[-1]['ctm']


def run():
    report = Notify()
    LOGGER.debug('Enter the Gate.')

    for symbol in conf.symbols:
        # Market open, check signal
        r = Result(symbol)
        r.get_signal()
        if not r.action:
            continue
        ts = report.setts(datetime.fromtimestamp(int(r.epoch_ms)/1000))
        LOGGER.info(f'Signal: {symbol}, {r.action}, {r.mode.upper()}, {r.price} at {ts}')
        LOGGER.debug(f'{symbol} - ' + r.df.tail(2).head(1).iloc[:, [0, 1, -4, -3, -2, -1]].to_string(header=False))
        LOGGER.debug(f'{symbol} - ' + r.df.tail(1).iloc[:, [0, 1, -4, -3, -2, -1]].to_string(header=False))

        # Check signal to open/close transaction
        if r.action.upper() in ('OPEN',):
            report.print_notify(f'>> {symbol}: Open-{r.mode.upper()} by {conf.volume} at {ts}, OK.')
        elif r.action.upper() in ('CLOSE',):
            report.print_notify(f'>> {symbol}: Close-{r.mode.upper()} at {ts}, OK.')


if __name__ == '__main__':
    run()
