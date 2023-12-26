from _init import *
from XTBApi.api import Client
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
    client = Client()
    client.login(conf.race_name, conf.race_pass, mode=conf.race_mode)
    gcp = Cloud()
    report = Notify(title=f'[{conf.race_mode}-{conf.algorithm}-{conf.period}]'.upper())
    LOGGER.debug('Enter the Gate.')

    # Check if market is open
    market_status = client.get_market_status(conf.symbols)
    LOGGER.info(f'{report.title} Market status: {market_status}')
    for symbol, status in market_status.items():
        if not status:
            continue

        # Market open, check signal
        r = Result(symbol)
        r.market_status = status
        r.get_signal(client=client)
        if not r.action:
            continue
        ts = report.setts(datetime.fromtimestamp(int(r.epoch_ms)/1000))
        LOGGER.info(f'Signal: {symbol}, {r.action}, {r.mode.upper()}, {r.price} at {ts}')
        LOGGER.debug(f'{symbol} - ' + r.df.tail(2).head(1).iloc[:, [0, 1, -4, -3, -2, -1]].to_string(header=False))
        LOGGER.debug(f'{symbol} - ' + r.df.tail(1).iloc[:, [0, 1, -4, -3, -2, -1]].to_string(header=False))

        # Check signal to open/close transaction
        if r.action in ('open', 'close'):
            if r.action in ('open',):
                res = trigger_open_trade(client, symbol=symbol, mode=r.mode)
                report.print_notify(
                    f'>> {symbol}: Open-{r.mode.upper()} by {conf.volume} at {ts}, {res}'
                )
            elif r.action in ('close',):
                res = trigger_close_trade(client, symbol=symbol, mode=r.mode)
                report.print_notify(
                    f'>> {symbol}: Close-{r.mode.upper()} at {ts}, {res}'
                )

    store_trade_rec(client, conf.race_name)
    client.logout()
    if report.texts:
        gcp.pub(f'{report.title}\n{report.texts}')


if __name__ == '__main__':
    run()
