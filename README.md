# xtb-auto
Auto trader using Api for XTB trading platform.


Prerequisite:
- Redis DB (for history candles storage)
- Google PubSub Topic (for mobile alert)

## Installing / Getting started

Just clone the repository, set env variables and parameters.

```bash
git clone https://github.com/Devnone21/xtb-auto.git
cd xtb-auto
cp .env.example .env
cp settings.json.example settings.json
# nano .env
# nano settings.json
# nano main.sh
```

Setup cron to trigger every period (default=15m)

```bash
crontab -e

# 1,16,31,46 * * * * /path_to/xtb-rsi/main.sh >>/tmp/xtb-rsi.log 2>>/tmp/xtb-error.log
```


Credit: use XTBApi like this simple tutorial.
```python
from XTBApi.api import Client
# FIRST INIT THE CLIENT
client = Client()
# THEN LOGIN
client.login("{user_id}", "{password}", mode={'demo','real'})
# CHECK IF MARKET IS OPEN FOR EURUSD
client.check_if_market_open(['EURUSD'])
# BUY ONE VOLUME (FOR EURUSD THAT CORRESPONDS TO 100000 units)
client.open_trade('buy', 'EURUSD', 1)
# SEE IF ACTUAL GAIN IS ABOVE 100 THEN CLOSE THE TRADE
trades = client.update_trades() # GET CURRENT TRADES
trade_ids = [trade_id for trade_id in trades.keys()]
for trade in trade_ids:
    actual_profit = client.get_trade_profit(trade) # CHECK PROFIT
    if actual_profit >= 100:
        client.close_trade(trade) # CLOSE TRADE
# CLOSE ALL OPEN TRADES
client.close_all_trades()
# THEN LOGOUT
client.logout()
```
