from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from timedelta import Timedelta
from finbert import estimate_sentiment
import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'

API_KEY = "PK4OSLTGBZXCCDMJ28GE"
API_SECRET = "fe83grqjoYVNY1vNkw9fIzafVIDylQfoWDlds3GX"
BASE_URL = "https://paper-api.alpaca.markets/v2"

ALPACA_CREDS = {
        "API_KEY":API_KEY,
        "API_SECRET":API_SECRET,
        "PAPER":True
}

class MLTrader(Strategy):
    def initialize(self, symbol:str="SPX", cash_at_risk:float=.5):
        self.symbol=symbol
        self.sleeptime = "24H"
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price)
        return cash, last_price, quantity

    def get_dates(self):
        today = self.get_datetime()
        prev_3_days = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), prev_3_days.strftime('%Y-%m-%d'),

    def get_sentiment(self):
        today, prev_3_days = self.get_dates()
        news = self.api.get_news(symbol=self.symbol, start = prev_3_days, end = today)

        news = [ev.__dict__["_raw"]["headline"]for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment()

        if cash > last_price:
            if sentiment == "positive" and probability > .999:
                if self.last_trade == "sell":
                    self.sell_all()
                order = self.create_order(
                        self.symbol,
                        quantity,
                        "buy",
                        type="bracket",
                        take_profit_price = last_price * 1.2,
                        stop_loss_price = last_price * .95
                    )
                self.submit_order(order)
                self.last_trade = "buy"

            elif sentiment == "negative" and probability > .999:
                if self.last_trade == "buy":
                    self.sell_all()
                order = self.create_order(
                        self.symbol,
                        quantity,
                        "sell",
                        type="bracket",
                        take_profit_price = last_price * .8,
                        stop_loss_price = last_price * 1.05
                    )
                self.submit_order(order)
                self.last_trade = "sell"

broker = Alpaca(ALPACA_CREDS)
strategy = MLTrader(name='mlstrat', broker=broker, parameters={"symbol":"SPX", "cash_at_risk":.5})


start_date = datetime(2020,1,1)
end_date = datetime(2024,11,28)

strategy.backtest(YahooDataBacktesting, start_date, end_date, parameters={"symbol":"SPX", "cash_at_risk":.5})

#trader = Trader()
#trader.add_strategy(strategy)
#trader.run_all()